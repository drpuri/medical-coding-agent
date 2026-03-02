# Coding Assistant Output Redesign — Claude Code Prompt

## Overview

Redesign the coding analysis output to have two views: **Provider View** (default) and **Detailed Coder View** (toggle). A toggle switch at the top of the output lets users switch between views. Both views contain the same information — Provider View is condensed and action-oriented, Detailed Coder View shows full coding rationale.

Every actionable recommendation across all sections gets a sequential number (Recommendation #1, #2, #3...) that is consistent across both views so a medical director can reference specific items by number.

---

## Top-of-Page Summary (Both Views)

Before any section content, display a dashboard summary:

- **E/M Code:** [code] — [one-line justification]
- **Diagnoses to Code:** [count]
- **HCC Captures:** [count confirmed] | [count action needed] | [count opportunities]
- **Documentation Actions:** [total count of numbered recommendations]
- **Frailty/Advanced Illness Exclusion:** [QUALIFIES / PARTIALLY QUALIFIES — action needed / DOES NOT QUALIFY]

This is the 5-second version. Everything below is the detail.

---

## View Toggle

Place a toggle switch at the top of the output, directly below the summary dashboard:

- **Provider View** (default) — condensed, action-oriented, copy-paste documentation language
- **Detailed Coder View** — full coding rationale, audit defensibility, regulatory references

All sections below describe BOTH views. The toggle switches the entire output, not individual sections.

---

## Section 1 — Billing Alerts

This section contains ONLY true stop-before-you-proceed alerts that change how you bill the entire encounter: hospice status, setting confirmation, split/shared visit, modifier requirements.

**DO NOT put clinical findings, documentation gaps, or compliance risks here.** Those belong in Tier 2 or the relevant tier where the provider takes action. If something was previously in billing alerts but is really a clinical decision or documentation gap (e.g., psychotropic medication specificity, unaddressed exam findings), move it to Tier 2.

Each alert is numbered and color-coded:
- 🔴 RED = stop, you have a problem that affects billing
- 🟡 YELLOW = action needed before submitting claim
- 🟢 GREEN = confirmed, no issue

### Provider View
One line per alert. Color badge. No explanation unless red.

Example:
```
🟢 No hospice — no modifier issues
🟢 Setting: SNF (POS 31) — Use 99307-99310
🟢 No split/shared visit concern
```

### Detailed Coder View
Same alerts, with full regulatory reasoning, F-tag references, CMS compliance notes, modifier logic.

---

## Section 2 — E/M Code Recommendation

### Provider View
Three lines max:
1. **Recommended code** + brief justification
2. **What would increase the code** (one line)
3. **What would decrease the code** (one line, only if relevant)

Example:
```
Recommended: 99308 — Low complexity MDM. Stable chronic conditions, no new data reviewed, low-risk management.

To support 99309: Document a chronic condition with exacerbation, new lab/imaging review, or active medication adjustment.
```

### Detailed Coder View
Full MDM breakdown:
- Number and complexity of problems (with detail)
- Data reviewed (with specifics)
- Risk of management (with reasoning)
- Full narrative on what would justify higher/lower code
- Reference to relevant coding guidelines

---

## Section 3 — Tier 1: Code These Now

These are conditions explicitly addressed in the Assessment & Plan that belong on today's claim.

Each diagnosis is displayed as a **card**. Cards are numbered as part of the global recommendation sequence.

### Provider View — Card Format

```
[Recommendation #X]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[CODE] — [Description]
HCC: [YES — HCC XX, RAF ~X.XXX] or [No]
Status: [✅ Supported as-is] or [⚠️ Action needed]

[If action needed, one-line explanation]
📋 Add to note: "[Exact copy-paste documentation language]"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Key rules for Provider View cards:
- No explanatory paragraphs
- No alternative code discussions
- No audit rationale
- Just: code, HCC status, whether action is needed, and if so exactly what to write
- The documentation language should be copy-pasteable — providers can drop it directly into their note

### Detailed Coder View — Card Format

Same card structure, but expanded to include:
- Full coding rationale and support documentation
- Specificity discussion (why F03.x should be G30.9 + F02.811, etc.)
- Alternative code options with reasoning
- Audit defensibility notes
- HCC recapture significance and RAF weight context

---

## Section 4 — Tier 2: Provider Should Confirm

These are conditions referenced in the exam, HPI, or medication list that lack a dedicated A&P entry but likely affect clinical decision-making. This is also where clinical findings that need a provider decision live (e.g., unaddressed exam findings, medication specificity issues, compliance-relevant documentation).

Each item is a **decision-tree card**. The tool asks the provider a clinical question and offers structured answer paths.

### Provider View — Decision Tree Card Format

```
[Recommendation #X]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ [Plain-language clinical question]
e.g., "Bilateral LE edema noted on exam but not in your A&P — what's causing it?"

Option A: [Clinical answer, e.g., "Dependent edema / immobility"]
  → Code: [R60.0]
  → 📋 Add to note: "[Exact documentation language for this path]"

Option B: [Clinical answer, e.g., "Venous insufficiency"]
  → Code: [I87.2]
  → 📋 Add to note: "[Exact documentation language for this path]"

Option C: [Clinical answer, e.g., "Possible heart failure"]
  → Code: [I50.9]  🔶 HCC 85, RAF ~0.323
  → 📋 Add to note: "[Exact documentation language for this path]"
  → Order: BNP, echocardiogram if not recently obtained

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If one of the decision paths leads to an HCC capture opportunity, flag it visually.

### Detailed Coder View

Same decision tree structure, plus:
- Full differential discussion
- Coding implications of each pathway
- Audit considerations for each option
- Related screening recommendations
- CMS compliance notes (e.g., F-tag references for psychotropic medications)
- Cross-references to how the decision affects other sections (e.g., frailty/advanced illness qualification)

---

## Section 5 — Tier 3: Documentation Flags

Conditions that appear in the history or background but are not connected to today's clinical reasoning. Do not code these today, but they represent future opportunities.

### Provider View
**Collapsed/accordion by default.** Each item is one line + expandable detail.

```
[Recommendation #X] Hypertension — likely present but not documented
  ▶ Expand for suggested documentation language

[Recommendation #X] CKD — not assessed, recommend screening
  ▶ Expand for suggested documentation language

[Recommendation #X] BMI/weight status — not documented
  ▶ Expand for suggested documentation language
```

When expanded, show the one-line action and copy-paste documentation language. Nothing more.

### Detailed Coder View
Full clinical rationale for why each item was flagged, prevalence data, screening recommendations, related HCC opportunities with RAF weights, combination coding implications.

---

## Section 6 — Documentation Gaps: REMOVED

**Do not create a separate Documentation Gaps section.** Every documentation gap is already captured as an action item within the relevant Tier 1, Tier 2, or Tier 3 card. A separate gaps section duplicates information and forces providers to read the same thing twice.

Instead, display a count badge in the Top-of-Page Summary: "X documentation improvements identified" — this count is the total number of recommendations that have an "Action needed" status across all tiers.

---

## Section 7 — HCC Capture Scorecard: SIDEBAR

Display as a persistent sidebar (desktop) or collapsible top panel (mobile). This is the at-a-glance view for medical directors.

### Provider View — Sidebar Format

| Condition | Status | Action |
|-----------|--------|--------|
| [Name] | ✅ Captured | — |
| [Name] | ⚠️ Action needed | See #X |
| [Name] | 🔶 Opportunity | See #X |

Each row is clickable/linked — jumps to the relevant recommendation card in the main body.

### Detailed Coder View — Sidebar Format

Same table with additional columns:
| Condition | HCC | RAF | Status | Action |
|-----------|-----|-----|--------|--------|

Show total potential RAF impact at the bottom of the sidebar.

---

## Section 8 — Frailty & Advanced Illness Exclusion Analysis

This section answers: Does this patient qualify for frailty/advanced illness HEDIS/Stars exclusions? Is it documented? If not, what needs to be documented based on this encounter?

### Provider View

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FRAILTY & ADVANCED ILLNESS EXCLUSION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Status: [QUALIFIES ✅ / PARTIALLY QUALIFIES ⚠️ / DOES NOT QUALIFY ❌]

Requirements: Patient 66+ [✅/❌] + Frailty indicators [✅/❌] + Advanced illness [✅/❌]

FRAILTY INDICATORS:
✅ Z74.1 — ADL assistance (documented)
✅ Z59.3 — Residential institution (documented)
⚠️ Gait/mobility abnormality — clinically likely, not documented
   [Recommendation #X] 📋 Add to note: "[Exact language]"

ADVANCED ILLNESS CONDITIONS:
✅ Dementia (F03.918 or specified equivalent) — documented
⚠️ Dementia medication dispensation — medications not named in note
   [Recommendation #X — references Tier 2 card] See Recommendation #X

WHAT'S MISSING:
[List only items with ⚠️ status — each references its recommendation number]

APPLICABLE MEASURE EXCLUSIONS:
[If qualifying, list specific HEDIS/Stars measures this patient can be excluded from]
e.g., BCS (Breast Cancer Screening), COL (Colorectal Cancer Screening), etc.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Key rules:
- Recommendations that require provider action in this section get their own sequential number
- If the action already exists in a Tier 2 card (e.g., "name the psychotropic medications"), reference that recommendation number instead of duplicating
- The "What's Missing" subsection only appears if the patient partially qualifies — it shows exactly what documentation would complete the qualification
- The "Applicable Measure Exclusions" subsection only appears if the patient qualifies or would qualify once missing items are documented

### Detailed Coder View
Same structure, plus:
- NCQA value set references
- Full criteria explanation for frailty and advanced illness definitions
- Measure-specific exclusion notes and criteria
- Interaction between frailty codes and other documented conditions
- Annual recapture considerations

---

## Frailty & Advanced Illness Logic

Build the frailty and advanced illness analysis using publicly available ICD-10 code lists from CMS HEDIS technical specifications. **Flag clearly in the code that these need to be validated against the current NCQA value sets before production deployment.**

### Frailty Indicators to Scan For:
Scan the note for diagnoses and documentation that map to these categories:
- Falls and fall risk (W01.x, W06, W10, W18, W19, R29.6)
- Malnutrition/underweight (E40-E46, E64.x, R63.0, R63.6, R64)
- Dementia (F01-F03, G30, G31.0, G31.1, G31.83)
- Pressure ulcers (L89.x)
- Impaired mobility / difficulty walking (R26.x, Z74.x, M62.81)
- BMI ≤22 or cachexia (Z68.1x, R64)
- Debility (R53.81, R54)
- Muscular weakness (M62.81)
- Need for assistance with personal care (Z74.1, Z74.2, Z74.3)
- Living in residential institution (Z59.3)
- Use of wheelchair/assistive devices (Z99.3)
- Incontinence (R32, N39.3, N39.4x, R15.x)
- Hearing/vision loss (H54.x, H90.x, H91.x)

### Advanced Illness Conditions to Scan For:
- Heart failure (I50.x)
- COPD/chronic lung disease (J41-J44, J47)
- Chronic kidney disease stage 4-5 (N18.4, N18.5, N18.6)
- Cancer/malignant neoplasms (C00-C96, active)
- Liver disease (K70-K77)
- ESRD (N18.6)
- Dementia (F01-F03, G30, G31.0, G31.1, G31.83)
- HIV/AIDS (B20)

### Qualification Logic:
Patient must be **age 66 or older** AND have:
1. At least ONE frailty indicator, AND
2. At least ONE advanced illness condition

Additionally check for:
- Dementia medication dispensation (donepezil, memantine, rivastigmine, galantamine) — this can substitute for or strengthen the advanced illness qualification
- Two or more outpatient visits, observation stays, ED visits, or non-acute inpatient encounters with advanced illness diagnosis in the measurement year or year prior

### Output:
- List all frailty indicators found with ICD-10 codes
- List all advanced illness conditions found with ICD-10 codes
- Identify what's documented vs. what's clinically likely but not documented
- For undocumented items, provide exact documentation language
- State qualification status clearly
- List applicable HEDIS measure exclusions if qualified

---

## General Formatting Rules

1. **Provider View uses minimal text.** No paragraphs of explanation. Cards, badges, one-liners, and copy-paste language only.
2. **Detailed Coder View preserves all current analytical depth.** Nothing is lost — it's just behind the toggle.
3. **Color coding is consistent:**
   - 🟢/✅ Green = confirmed, no action needed
   - 🟡/⚠️ Yellow = action needed from provider
   - 🔴/🛑 Red = stop, problem affects billing
   - 🔶 Orange = HCC opportunity
4. **Copy-paste documentation language** appears in a visually distinct format (monospace, highlighted box, or similar) so providers can identify it instantly and drop it into their note.
5. **Cross-references use recommendation numbers.** If Tier 2 Recommendation #7 is referenced in the Frailty section, it says "See Recommendation #7" — not a paragraph re-explaining the issue.
6. **The HCC sidebar is always visible** in both views (collapsed on mobile).
7. **Tier 3 is collapsed by default** in Provider View.

---

## Important Note on Value Sets

The frailty indicator and advanced illness code lists above are based on publicly available CMS HEDIS technical specifications and are approximate. **These must be validated against the current NCQA value sets before production deployment.** Add a small disclaimer in the Frailty & Advanced Illness section: "Frailty and advanced illness logic based on CMS HEDIS specifications. Validate against current NCQA value sets for production use."
