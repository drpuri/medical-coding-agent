"""
CMS HCC Model V28 — Conditions most relevant to SNF/ALF primary care population.
Used to enrich agent output with HCC flags without requiring an API call.

Source: CMS 2024 HCC Model V28
"""

# Format: ICD-10 prefix or exact code → (HCC category number, description, relative weight note)
# Weights are approximate — actual RAF depends on demographics and model year

HCC_MAP = {
    # Diabetes
    "E10": (35, "Type 1 Diabetes with Complications", "high"),
    "E11.0": (35, "Diabetes with Hyperosmolarity", "high"),
    "E11.1": (35, "Diabetes with Ketoacidosis", "high"),
    "E11.2": (37, "Diabetes with Kidney Complications", "high"),
    "E11.3": (36, "Diabetes with Ophthalmic Complications", "moderate"),
    "E11.4": (36, "Diabetes with Neurological Complications", "moderate"),
    "E11.5": (37, "Diabetes with Circulatory Complications", "moderate"),
    "E11.6": (38, "Diabetes with Other Complications", "moderate"),
    "E11.9": (38, "Type 2 Diabetes without Complications", "lower"),

    # Heart Failure
    "I50.2": (85, "Systolic Heart Failure", "high"),
    "I50.3": (85, "Diastolic Heart Failure", "high"),
    "I50.4": (85, "Combined Systolic/Diastolic Heart Failure", "high"),
    "I50.9": (85, "Heart Failure, Unspecified", "high"),

    # CAD / Ischemic Heart Disease
    "I25.1": (87, "Atherosclerotic Heart Disease", "high"),
    "I25.7": (87, "Atherosclerosis of Coronary Artery Bypass Graft", "high"),
    "I25.8": (86, "Other Chronic Ischemic Heart Disease", "high"),

    # CKD
    "N18.1": (139, "CKD Stage 1", "lower"),
    "N18.2": (139, "CKD Stage 2", "lower"),
    "N18.3": (138, "CKD Stage 3", "moderate"),
    "N18.4": (138, "CKD Stage 4", "moderate"),
    "N18.5": (137, "CKD Stage 5 (pre-dialysis)", "high"),
    "N18.6": (136, "End Stage Renal Disease", "very high"),

    # Dementia
    "F01.5": (51, "Vascular Dementia", "high"),
    "F02.8": (52, "Dementia in Other Diseases", "high"),
    "F03.9": (51, "Unspecified Dementia", "high"),
    "G30":   (52, "Alzheimer's Disease", "high"),

    # COPD / Pulmonary
    "J44": (111, "COPD", "moderate"),
    "J43": (111, "Emphysema", "moderate"),
    "J45": (110, "Asthma", "moderate"),

    # Stroke / Neurological
    "I63": (100, "Cerebral Infarction", "high"),
    "I69": (100, "Sequelae of Cerebrovascular Disease", "high"),
    "G35": (77, "Multiple Sclerosis", "high"),

    # Malnutrition
    "E40":  (21, "Kwashiorkor", "high"),
    "E41":  (21, "Nutritional Marasmus", "high"),
    "E42":  (21, "Marasmic Kwashiorkor", "high"),
    "E43":  (21, "Severe Protein-Calorie Malnutrition", "high"),
    "E44.0":(21, "Moderate Protein-Calorie Malnutrition", "high"),

    # Peripheral Vascular
    "I70.2": (107, "Atherosclerosis of Native Arteries of Extremities", "high"),
    "I96":   (106, "Gangrene", "very high"),

    # Pressure Ulcers
    "L89.0": (157, "Pressure Ulcer of Elbow", "high"),
    "L89.1": (157, "Pressure Ulcer of Back", "high"),
    "L89.2": (157, "Pressure Ulcer of Hip", "high"),
    "L89.3": (157, "Pressure Ulcer of Buttock", "high"),

    # Psychiatric
    "F20":  (57, "Schizophrenia", "high"),
    "F31":  (58, "Bipolar Disorder", "moderate"),
    "F33":  (59, "Major Depressive Disorder, Recurrent", "moderate"),
}


def get_hcc_flag(icd10_code: str) -> dict | None:
    """
    Check if an ICD-10 code maps to an HCC category.
    Returns HCC info dict or None if not HCC-relevant.
    
    Checks exact code first, then progressively shorter prefixes.
    """
    code = icd10_code.strip().upper()
    
    # Try exact match first, then truncate progressively
    for length in [len(code), 5, 4, 3]:
        prefix = code[:length]
        if prefix in HCC_MAP:
            hcc_num, description, weight = HCC_MAP[prefix]
            return {
                "hcc_category": hcc_num,
                "description": description,
                "relative_weight": weight,
                "requires_annual_recapture": True,
                "note": "Must be documented with supporting clinical evidence every plan year for MA risk adjustment"
            }
    
    return None


def get_all_hcc_flags(icd10_codes: list[str]) -> dict:
    """
    Check a list of codes against the HCC map.
    Returns a summary of HCC-relevant codes found.
    """
    hcc_codes = {}
    non_hcc_codes = []
    
    for code in icd10_codes:
        flag = get_hcc_flag(code)
        if flag:
            hcc_codes[code] = flag
        else:
            non_hcc_codes.append(code)
    
    return {
        "hcc_relevant": hcc_codes,
        "non_hcc": non_hcc_codes,
        "hcc_count": len(hcc_codes)
    }
