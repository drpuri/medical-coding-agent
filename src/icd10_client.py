"""
ICD-10 client — wraps the CMS ICD-10 API.
All functions return plain dicts so the agent can serialize them as tool results.
"""

import requests
from typing import Optional

BASE_URL = "https://clinicaltables.nlm.nih.gov/api/icd10cm/v3"


def lookup_code(code: str) -> dict:
    """
    Look up a specific ICD-10-CM code.
    Returns code details or an error dict.
    """
    code = code.strip().upper()

    # NLM clinical tables API — free, no key required
    url = f"{BASE_URL}/search"
    params = {
        "sf": "code",
        "terms": code,
        "maxList": 10,
        "df": "code,name"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Response format: [total, codes_array, extra, display_array]
        if data[0] == 0:
            return {"found": False, "code": code, "message": "Code not found in ICD-10-CM database"}

        # Find exact match
        codes = data[1]
        displays = data[3]

        for i, c in enumerate(codes):
            if c.upper() == code:
                return {
                    "found": True,
                    "code": c,
                    "description": displays[i][1] if displays else "Description unavailable",
                    "valid_for_billing": True  # NLM only returns billable codes
                }

        # Return closest match if exact not found
        return {
            "found": False,
            "code": code,
            "message": f"Exact code not found. Closest match: {codes[0]} — {displays[0][1] if displays else 'N/A'}"
        }

    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}", "code": code}


def search_codes(query: str, limit: int = 5) -> dict:
    """
    Search ICD-10-CM codes by description.
    Returns list of matching codes with descriptions.
    """
    url = f"{BASE_URL}/search"
    params = {
        "sf": "name",
        "terms": query,
        "maxList": limit,
        "df": "code,name"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data[0] == 0:
            return {"results": [], "query": query, "message": "No matching codes found"}

        results = []
        codes = data[1]
        displays = data[3]

        for i, code in enumerate(codes):
            results.append({
                "code": code,
                "description": displays[i][1] if displays else "N/A"
            })

        return {
            "query": query,
            "total_found": data[0],
            "results": results
        }

    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}", "query": query}


def get_hierarchy(code_prefix: str) -> dict:
    """
    Get all subcodes under a given ICD-10 prefix.
    Useful for showing providers all specificity options for a condition.
    """
    code_prefix = code_prefix.strip().upper()

    url = f"{BASE_URL}/search"
    params = {
        "sf": "code",
        "terms": code_prefix,
        "maxList": 30,
        "df": "code,name"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data[0] == 0:
            return {
                "prefix": code_prefix,
                "subcodes": [],
                "message": "No codes found under this prefix"
            }

        subcodes = []
        codes = data[1]
        displays = data[3]

        for i, code in enumerate(codes):
            if code.startswith(code_prefix):
                subcodes.append({
                    "code": code,
                    "description": displays[i][1] if displays else "N/A"
                })

        return {
            "prefix": code_prefix,
            "total": len(subcodes),
            "subcodes": subcodes
        }

    except requests.RequestException as e:
        return {"error": f"API request failed: {str(e)}", "prefix": code_prefix}
