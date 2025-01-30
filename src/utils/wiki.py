"""
Wikipedia/Wikidata utilities for fetching person information
"""

import time
import logging
from functools import lru_cache
from datetime import datetime
import requests
from typing import Optional, Dict, Any

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def fetch_wikidata(params: Dict[str, Any], retries: int = 3, delay: int = 2) -> Optional[Dict[str, Any]]:
    """Fetch Wikidata with retries on failure.

    Args:
        params: Request parameters for the Wikidata API
        retries: Number of retries before giving up
        delay: Delay in seconds between retries

    Returns:
        JSON response from the API, or None if all retries fail
    """
    for attempt in range(retries):
        try:
            response = requests.get(
                "https://www.wikidata.org/w/api.php",
                params=params,
                timeout=5
            )
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, ValueError) as e:
            logger.error("Attempt %s failed: %s", attempt + 1, e)
            if attempt < retries - 1:
                time.sleep(delay)
            continue

    logger.warning("All retries failed for Wikidata fetch")
    return None

def resolve_redirect(title: str) -> str:
    """Resolve Wikipedia page redirects.

    Args:
        title: Page URL title (end of URL)

    Returns:
        Fully resolved title
    """
    wikipedia_api_url = "https://en.wikipedia.org/w/api.php"

    def query_wikipedia(t: str) -> Dict[str, Any]:
        params = {
            "action": "query",
            "titles": t,
            "redirects": 1,
            "format": "json"
        }
        response = requests.get(wikipedia_api_url, params=params, timeout=5)
        return response.json()

    data = query_wikipedia(title)

    # Follow all redirects
    while "redirects" in data.get("query", {}):
        redirects = data["query"]["redirects"]
        final_redirect = redirects[-1]["to"]
        data = query_wikipedia(final_redirect)

    if "normalized" in data.get("query", {}):
        final_title = data["query"]["normalized"][0]["to"]
    elif "pages" in data.get("query", {}):
        page_id = next(iter(data["query"]["pages"]))
        final_title = data["query"]["pages"][page_id]["title"]
    else:
        final_title = title

    return final_title

def get_wiki_id_from_page(page_title: str) -> Optional[str]:
    """Get Wikidata ID from Wikipedia page title.

    Args:
        page_title: Page URL title (end of URL)

    Returns:
        Wiki Data identifier or None if not found
    """
    if not page_title:
        return None

    final_title = resolve_redirect(page_title)
    params = {
        "action": "wbgetentities",
        "format": "json",
        "sites": "enwiki",
        "titles": final_title,
        "languages": "en",
        "redirects": "yes"
    }
    
    data = fetch_wikidata(params)
    if not data or "entities" not in data or not data["entities"]:
        return None

    entity_id = next(iter(data["entities"]))
    return None if entity_id == "-1" else entity_id

@lru_cache(maxsize=128)
def get_birth_death_date(wikidata_prop_id: str, wikidata_q_number: str) -> Optional[datetime]:
    """Get birth or death date from Wikidata.

    Args:
        wikidata_prop_id: Property ID, P569 (birth) or P570 (death)
        wikidata_q_number: Wiki Data ID (Q Number)

    Returns:
        Date of the requested entity, or None if not found
    """
    if not wikidata_q_number:
        return None

    params = {
        "action": "wbgetentities",
        "ids": wikidata_q_number,
        "format": "json",
        "languages": "en"
    }

    data = fetch_wikidata(params)
    if not data or "entities" not in data or wikidata_q_number not in data["entities"]:
        logger.warning("Invalid data for %s", wikidata_q_number)
        return None

    try:
        claims = data["entities"][wikidata_q_number]["claims"]
        if wikidata_prop_id not in claims:
            logger.info("Property %s not found for %s", wikidata_prop_id, wikidata_q_number)
            return None

        date_str = claims[wikidata_prop_id][0]["mainsnak"]["datavalue"]["value"]["time"]
    except (KeyError, IndexError, TypeError) as e:
        logger.warning("Error accessing date data: %s", e)
        return None

    # Remove leading +/- from date string
    if date_str.startswith(("+", "-")):
        date_str = date_str[1:]

    try:
        if date_str.endswith("-00-00T00:00:00Z"):
            date_obj = datetime.strptime(date_str, "%Y-00-00T00:00:00Z")
        elif date_str[5:7] != "00" and date_str.endswith("-00T00:00:00Z"):
            date_obj = datetime.strptime(date_str, "%Y-%m-00T00:00:00Z")
        else:
            date_obj = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as e:
        logger.error("Error parsing date %s: %s", date_str, e)
        return None

    return date_obj

def calculate_age(birth_date: datetime, death_date: Optional[datetime] = None) -> int:
    """Calculate age based on birth date and optional death date.

    Args:
        birth_date: Date of birth
        death_date: Date of death (if applicable)

    Returns:
        Calculated age
    """
    if not birth_date:
        return 0

    end_date = death_date if death_date else datetime.now()
    age = end_date.year - birth_date.year

    # Adjust age if birthday hasn't occurred this year
    if (end_date.month, end_date.day) < (birth_date.month, birth_date.day):
        age -= 1

    return max(0, age)