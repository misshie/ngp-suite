import requests
import json
from typing import List, Dict, Any

# Define API endpoints
PCF_RANKED_LIST_API_URL = "https://pubcasefinder.dbcls.jp/api/pcf_get_ranked_list"
PCF_HPO_DATA_API_URL = "https://pubcasefinder.dbcls.jp/api/pcf_get_hpo_data_by_hpo_id"

def _fetch_ranked_list(hpo_ids: List[str]) -> List[Dict[str, Any]]:
    """Fetches the ranked list of diseases from PubCaseFinder."""
    params = {
        'target': 'omim',
        'format': 'json',
        'hpo_id': ','.join(hpo_ids)
    }
    response = requests.get(PCF_RANKED_LIST_API_URL, params=params, timeout=90)
    response.raise_for_status()
    return response.json()

def _fetch_hpo_names(hpo_ids: List[str]) -> Dict[str, Any]:
    """Fetches HPO term names from PubCaseFinder."""
    params = {'hpo_id': ','.join(hpo_ids)}
    response = requests.get(PCF_HPO_DATA_API_URL, params=params, timeout=90)
    response.raise_for_status()
    return response.json()

def query_pubcasefinder(hpo_ids: List[str]) -> Dict[str, Any]:
    """
    Queries PubCaseFinder for both ranked disease list and HPO term names.

    Args:
        hpo_ids: A list of HPO term IDs.

    Returns:
        A dictionary containing both the ranked list and HPO name data,
        or an error message if any query fails.
    """
    if not hpo_ids:
        return {}

    print(f"Querying PubCaseFinder with HPO IDs: {hpo_ids}")

    try:
        # Fetch both sets of data from the API
        ranked_list = _fetch_ranked_list(hpo_ids)
        hpo_names = _fetch_hpo_names(hpo_ids)

        # --- Debugging Output ---
        print("--- PubCaseFinder Ranked List Response (Truncated) ---")
        print(json.dumps(ranked_list, indent=2)[:500] + "\n...")
        print("----------------------------------------------------")
        
        # Combine both results into a single object
        return {
            "ranked_list": ranked_list,
            "hpo_names": hpo_names
        }

    except requests.exceptions.RequestException as e:
        print(f"Error querying PubCaseFinder: {e}")
        return {"error": "Failed to connect to the PubCaseFinder API."}
