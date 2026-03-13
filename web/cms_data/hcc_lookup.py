"""CMS-HCC V28 Deterministic Lookup Tables

Source: CMS 2025 Midyear/Final ICD-10-CM Mappings (Excel)
        + CMS 2024 Rate Announcement Table VIII-1 (PDF pages 183-191)
Model:  V28 Community NonDual Aged (CNA) Continuing Enrollees
Year:   Payment Year 2026 (100% V28)

Usage:
    from hcc_lookup import lookup_icd10, enrich_hcc_results

    # Single code lookup
    result = lookup_icd10("E1165")
    # Returns: [{"hcc": 38, "label": "...", "raf_weight": 0.166}]

    # Process LLM output - replace hallucinated HCC/RAF with deterministic values
    enriched = enrich_hcc_results(llm_icd_codes)
"""

import json
import os

_DIR = os.path.dirname(os.path.abspath(__file__))

# Lazy-loaded caches
_icd_to_hcc = None
_hcc_coefficients = None
_hcc_labels = None
_hierarchies = None
_interactions = None
_upgrades = None


def _load(filename):
    with open(os.path.join(_DIR, filename)) as f:
        return json.load(f)


def get_icd_to_hcc():
    """Load ICD-10-CM -> HCC V28 mapping (7,903 codes)."""
    global _icd_to_hcc
    if _icd_to_hcc is None:
        _icd_to_hcc = _load("v28_icd10_to_hcc.json")
    return _icd_to_hcc


def get_hcc_coefficients():
    """Load HCC -> RAF weight coefficients (115 HCCs, CNA segment)."""
    global _hcc_coefficients
    if _hcc_coefficients is None:
        _hcc_coefficients = _load("v28_hcc_coefficients_cna.json")
    return _hcc_coefficients


def get_hcc_labels():
    """Load HCC number -> description labels."""
    global _hcc_labels
    if _hcc_labels is None:
        _hcc_labels = _load("v28_hcc_labels.json")
    return _hcc_labels


def get_hierarchies():
    """Load HCC hierarchy rules (which HCCs supersede which)."""
    global _hierarchies
    if _hierarchies is None:
        raw = _load("v28_hcc_hierarchies.json")
        # Convert to int keys/values, skip metadata keys
        _hierarchies = {}
        for k, v in raw.items():
            if not k.startswith("_"):
                _hierarchies[int(k)] = [int(x) for x in v]
    return _hierarchies


def get_interactions():
    """Load CNA disease interaction terms and coefficients."""
    global _interactions
    if _interactions is None:
        raw = _load("v28_interactions_cna.json")
        _interactions = raw.get("interactions", [])
    return _interactions


def get_upgrades():
    """Load HCC specificity upgrade map."""
    global _upgrades
    if _upgrades is None:
        raw = _load("v28_hcc_upgrades.json")
        # Convert to int keys, skip metadata keys
        _upgrades = {}
        for k, v in raw.items():
            if not k.startswith("_"):
                _upgrades[int(k)] = v
    return _upgrades


def normalize_icd10(code):
    """Normalize ICD-10 code: remove dots, uppercase, strip whitespace."""
    if not code:
        return ""
    return code.replace(".", "").replace(" ", "").strip().upper()


def lookup_icd10(icd10_code):
    """Look up HCC categories and RAF weights for an ICD-10-CM code.

    Args:
        icd10_code: ICD-10-CM code (e.g., "E11.65" or "E1165")

    Returns:
        List of dicts, each with:
            - hcc: int, HCC category number
            - label: str, HCC description
            - raf_weight: float, CNA coefficient
        Empty list if code does not map to any HCC.
    """
    code = normalize_icd10(icd10_code)
    if not code:
        return []

    icd_map = get_icd_to_hcc()
    coefficients = get_hcc_coefficients()
    labels = get_hcc_labels()

    hcc_numbers = icd_map.get(code, [])
    results = []
    for hcc_num in hcc_numbers:
        hcc_str = str(hcc_num)
        results.append({
            "hcc": hcc_num,
            "label": labels.get(hcc_str, f"HCC {hcc_num}"),
            "raf_weight": coefficients.get(hcc_str, 0.0),
        })
    return results


def apply_hierarchies(hcc_set):
    """Apply CMS V28 disease hierarchies to a set of HCC numbers.

    When a severe HCC is present, it supersedes (zeroes out) milder HCCs
    in the same disease group, per the official CMS SAS macro V28115H1.

    Args:
        hcc_set: set of int HCC numbers

    Returns:
        Dict mapping each HCC (int) to either None (active) or
        the int HCC number that supersedes it.
    """
    hierarchies = get_hierarchies()
    status = {hcc: None for hcc in hcc_set}  # None = active

    for superior, inferiors in hierarchies.items():
        if superior in hcc_set:
            for inf in inferiors:
                if inf in status and status[inf] is None:
                    status[inf] = superior  # mark as superseded

    return status


def calculate_interactions(active_hccs):
    """Check for CNA disease interaction terms given active (post-hierarchy) HCCs.

    Args:
        active_hccs: set of int HCC numbers (after hierarchy application)

    Returns:
        List of dicts, each with:
            - label: str, human-readable interaction name
            - coefficient: float, bonus RAF weight
            - groups: dict of group name -> list of matching HCCs from patient
    """
    interactions = get_interactions()
    triggered = []

    for term in interactions:
        matched_groups = {}
        all_groups_hit = True
        for group_name, group_hccs in term["groups"].items():
            hits = [h for h in group_hccs if h in active_hccs]
            if hits:
                matched_groups[group_name] = hits
            else:
                all_groups_hit = False
                break

        if all_groups_hit:
            triggered.append({
                "label": term["label"],
                "coefficient": term["coefficient"],
                "groups": matched_groups,
            })

    return triggered


def get_specificity_upgrades(hcc_num):
    """For a given HCC, return possible higher-severity upgrades with RAF deltas.

    Args:
        hcc_num: int HCC number

    Returns:
        Dict with label, current raf, and upgrades list, or None if no upgrades.
    """
    upgrades = get_upgrades()
    return upgrades.get(hcc_num)


def enrich_hcc_results(icd_codes):
    """Process a list of ICD-10 codes and return deterministic HCC/RAF data.

    This replaces the LLM-generated HCC fields with authoritative CMS data.
    Applies V28 hierarchies and calculates interaction bonuses.

    Args:
        icd_codes: List of ICD-10-CM code strings from LLM output

    Returns:
        Dict with:
            - hcc_categories: list of unique HCC entries (with superseded_by field)
            - total_disease_raf: float, post-hierarchy sum + interaction bonuses
            - interactions: list of triggered interaction terms
            - codes_with_hcc: int, count of codes mapping to at least one HCC
            - codes_without_hcc: int, count of codes with no HCC mapping
    """
    seen_hccs = {}  # hcc_num -> {label, raf_weight}
    codes_with = 0
    codes_without = 0

    for code in icd_codes:
        results = lookup_icd10(code)
        if results:
            codes_with += 1
            for r in results:
                if r["hcc"] not in seen_hccs:
                    seen_hccs[r["hcc"]] = {
                        "hcc": r["hcc"],
                        "label": r["label"],
                        "raf_weight": r["raf_weight"],
                        "icd10_codes": [],
                    }
                seen_hccs[r["hcc"]]["icd10_codes"].append(normalize_icd10(code))
        else:
            codes_without += 1

    # Apply hierarchies
    hcc_set = set(seen_hccs.keys())
    hier_status = apply_hierarchies(hcc_set)

    # Mark superseded HCCs
    for hcc_num, entry in seen_hccs.items():
        sup = hier_status.get(hcc_num)
        entry["superseded_by"] = f"HCC {sup}" if sup else None

    # Get active (non-superseded) HCCs
    active_hccs = {h for h, sup in hier_status.items() if sup is None}

    # Calculate interactions on active HCCs
    interactions = calculate_interactions(active_hccs)
    interaction_bonus = round(sum(i["coefficient"] for i in interactions), 3)

    # Total RAF = sum of active HCCs + interaction bonuses
    active_raf = sum(
        seen_hccs[h]["raf_weight"] for h in active_hccs if h in seen_hccs
    )
    total_raf = round(active_raf + interaction_bonus, 3)

    hcc_list = sorted(seen_hccs.values(), key=lambda x: x["raf_weight"], reverse=True)

    return {
        "hcc_categories": hcc_list,
        "total_disease_raf": total_raf,
        "interactions": interactions,
        "interaction_bonus": interaction_bonus,
        "codes_with_hcc": codes_with,
        "codes_without_hcc": codes_without,
    }


if __name__ == "__main__":
    # Self-test with a realistic SNF patient:
    # E11.65 (DM2 w/ hyperglycemia -> HCC 38), E11.9 (DM2 unspecified -> HCC 38 too, same HCC)
    # I50.22 (systolic CHF chronic -> HCC 226), J44.9 (COPD -> HCC 280)
    # N18.4 (CKD stage 4 -> HCC 327), G30.9 (Alzheimer's -> HCC 127)
    # I48.20 (AFib -> HCC 238)
    test_codes = ["E11.65", "I50.22", "J44.9", "N18.4", "F43.10", "G30.9", "I48.20"]
    print("=== HCC Lookup Self-Test ===\n")
    for code in test_codes:
        results = lookup_icd10(code)
        if results:
            for r in results:
                print(f"  {code} -> HCC {r['hcc']} ({r['label']}) RAF={r['raf_weight']}")
        else:
            print(f"  {code} -> No HCC mapping")

    print("\n=== Hierarchy Test ===")
    print("  Codes: E11.65 (HCC 38) + E11.9 (HCC 38) — same HCC, no hierarchy effect")
    print("  Codes: I50.22 (HCC 226) + I50.9 (HCC 227) — 226 supersedes 227")
    hier_test = {"E11.65", "I50.22", "I50.9"}
    all_hccs = set()
    for code in hier_test:
        for r in lookup_icd10(code):
            all_hccs.add(r["hcc"])
    print(f"  All HCCs before hierarchy: {sorted(all_hccs)}")
    status = apply_hierarchies(all_hccs)
    for hcc, sup in sorted(status.items()):
        label = "ACTIVE" if sup is None else f"superseded by HCC {sup}"
        print(f"    HCC {hcc}: {label}")

    print("\n=== Interaction Test ===")
    print("  Patient with CHF (HCC 226) + COPD (HCC 280) + CKD4 (HCC 327) + AFib (HCC 238)")
    active = {226, 280, 327, 238}
    interactions = calculate_interactions(active)
    for ix in interactions:
        print(f"    {ix['label']}: +{ix['coefficient']} RAF")

    print("\n=== Specificity Upgrade Test ===")
    for test_hcc in [227, 38, 127, 329]:
        up = get_specificity_upgrades(test_hcc)
        if up:
            print(f"  HCC {test_hcc} ({up['label']}, RAF {up['raf']}):")
            for u in up["upgrades"][:2]:
                print(f"    -> HCC {u['hcc']} ({u['label']}) RAF {u['raf']} (+{u['delta']})")

    print("\n=== Full Enrichment Test (with hierarchies + interactions) ===\n")
    enriched = enrich_hcc_results(test_codes)
    print(f"  Adjusted RAF: {enriched['total_disease_raf']}")
    print(f"  Interaction bonus: {enriched['interaction_bonus']}")
    print(f"  Codes with HCC: {enriched['codes_with_hcc']}")
    print(f"  Codes without HCC: {enriched['codes_without_hcc']}")
    for cat in enriched["hcc_categories"]:
        sup = f" [SUPERSEDED by {cat['superseded_by']}]" if cat.get("superseded_by") else ""
        print(f"    HCC {cat['hcc']}: {cat['label']} (RAF={cat['raf_weight']}) <- {cat['icd10_codes']}{sup}")
    for ix in enriched.get("interactions", []):
        print(f"    Interaction: {ix['label']} -> +{ix['coefficient']} RAF")
