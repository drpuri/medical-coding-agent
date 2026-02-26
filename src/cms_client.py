"""
CMS Coverage client — wraps the CMS Coverage Database API for NCD lookups.
"""

import requests
from typing import Optional

BASE_URL = "https://api.coverage-api.cms.gov/v1"


def search_ncd(keyword: str, limit: int = 3) -> dict:
    """
    Search National Coverage Determinations by keyword.
    Returns policy summaries relevant to the keyword.
    """
    url = f"{BASE_URL}/ncd"
    params = {
        "keyword": keyword,
        "limit": limit,
        "sortBy": "title",
        "sortOrder": "asc"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        items = data.get("items", [])
        if not items:
            return {
                "keyword": keyword,
                "results": [],
                "message": "No NCDs found for this keyword"
            }

        results = []
        for item in items[:limit]:
            results.append({
                "title": item.get("title"),
                "document_id": item.get("document_id"),
                "last_updated": item.get("last_updated"),
                "summary": item.get("summary", "See full document for details")
            })

        return {
            "keyword": keyword,
            "total_found": data.get("total", len(results)),
            "results": results
        }

    except requests.RequestException as e:
        return {"error": f"CMS API request failed: {str(e)}", "keyword": keyword}
