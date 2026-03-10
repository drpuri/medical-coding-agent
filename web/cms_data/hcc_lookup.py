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


def enrich_hcc_results(icd_codes):
    """Process a list of ICD-10 codes and return deterministic HCC/RAF data.

    This replaces the LLM-generated HCC fields with authoritative CMS data.

    Args:
        icd_codes: List of ICD-10-CM code strings from LLM output

    Returns:
        Dict with:
            - hcc_categories: list of unique HCC entries found
            - total_raf: float, sum of all unique HCC RAF weights
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

    hcc_list = sorted(seen_hccs.values(), key=lambda x: x["raf_weight"], reverse=True)
    total_raf = round(sum(h["raf_weight"] for h in hcc_list), 3)

    return {
        "hcc_categories": hcc_list,
        "total_disease_raf": total_raf,
        "codes_with_hcc": codes_with,
        "codes_without_hcc": codes_without,
    }


if __name__ == "__main__":
    # Self-test
    test_codes = ["E11.65", "I50.22", "J44.9", "N18.4", "F43.10", "G30.9", "I48.20"]
    print("=== HCC Lookup Self-Test ===\n")
    for code in test_codes:
        results = lookup_icd10(code)
        if results:
            for r in results:
                print(f"  {code} -> HCC {r['hcc']} ({r['label']}) RAF={r['raf_weight']}")
        else:
            print(f"  {code} -> No HCC mapping")

    print("\n=== Batch Enrichment Test ===\n")
    enriched = enrich_hcc_results(test_codes)
    print(f"  Total disease RAF: {enriched['total_disease_raf']}")
    print(f"  Codes with HCC: {enriched['codes_with_hcc']}")
    print(f"  Codes without HCC: {enriched['codes_without_hcc']}")
    for cat in enriched["hcc_categories"]:
        print(f"    HCC {cat['hcc']}: {cat['label']} (RAF={cat['raf_weight']}) <- {cat['icd10_codes']}")
