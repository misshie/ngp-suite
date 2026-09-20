import requests
import json
from typing import List, Dict, Any

# Define API endpoints
PCF_RANKED_LIST_API_URL = "https://pubcasefinder.dbcls.jp/api/pcf_get_ranked_list"
PCF_HPO_DATA_API_URL = "https://pubcasefinder.dbcls.jp/api/pcf_get_hpo_data_by_hpo_id"


def _log_request_error(label: str, fallback_url: str, e: requests.exceptions.RequestException) -> None:
    """Log PubCaseFinder request failures with status code and URL when available."""
    response = getattr(e, "response", None)
    status = getattr(response, "status_code", None)
    url = getattr(response, "url", None) or fallback_url
    if status is not None:
        print(f"Error querying PubCaseFinder {label}: HTTP {status} url={url}")
    else:
        print(f"Error querying PubCaseFinder {label}: url={url} ({e})")


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

    Each endpoint is queried independently so a failure on one side does not
    discard a successful response from the other.

    Args:
        hpo_ids: A list of HPO term IDs.

    Returns:
        A dictionary that may contain ranked_list and/or hpo_names.
        If both queries fail, returns an error message.
    """
    if not hpo_ids:
        return {}

    print(f"Querying PubCaseFinder with HPO IDs: {hpo_ids}")

    result: Dict[str, Any] = {}

    try:
        ranked_list = _fetch_ranked_list(hpo_ids)
        print("--- PubCaseFinder Ranked List Response (Truncated) ---")
        print(json.dumps(ranked_list, indent=2)[:500] + "\n...")
        print("----------------------------------------------------")
        result["ranked_list"] = ranked_list
    except requests.exceptions.RequestException as e:
        _log_request_error("ranked_list", PCF_RANKED_LIST_API_URL, e)

    try:
        result["hpo_names"] = _fetch_hpo_names(hpo_ids)
    except requests.exceptions.RequestException as e:
        _log_request_error("hpo_names", PCF_HPO_DATA_API_URL, e)

    if not result:
        return {"error": "Failed to connect to the PubCaseFinder API."}

    return result
