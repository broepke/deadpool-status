"""
Wikipedia/Wikidata utilities for fetching person information
"""

import time
import logging
import json
from functools import lru_cache
from datetime import datetime
import requests
from typing import Optional, Dict, Any

# Configure logging
logger = logging.getLogger()

def fetch_wikidata(params: Dict[str, Any], retries: int = 3, delay: int = 1) -> Optional[Dict[str, Any]]:
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
            logger.info(f"Wikidata API request: {json.dumps(params)}")
            response = requests.get(
                "https://www.wikidata.org/w/api.php",
                params=params,
                timeout=5
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"Wikidata API response: {json.dumps(data)}")
            return data
        except (requests.exceptions.RequestException, ValueError) as e:
            logger.error("Attempt %s failed: %s", attempt + 1, e)
            if attempt < retries - 1:
                time.sleep(delay)
            continue

    logger.warning("All retries failed for Wikidata fetch")
    return None

def resolve_redirect(title: str) -> Optional[str]:
    """Resolve Wikipedia page redirects.

    Args:
        title: Page URL title (end of URL)

    Returns:
        Fully resolved title or None if not found
    """
    try:
        logger.info(f"Resolving Wikipedia page: {title}")
        wikipedia_api_url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "titles": title,
            "redirects": 1,
            "format": "json"
        }
        response = requests.get(wikipedia_api_url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Wikipedia API response: {json.dumps(data)}")

        # Handle redirects
        if "redirects" in data.get("query", {}):
            redirects = data["query"]["redirects"]
            title = redirects[-1]["to"]
            logger.info(f"Resolved redirect to: {title}")

        # Handle normalized titles
        if "normalized" in data.get("query", {}):
            title = data["query"]["normalized"][0]["to"]
            logger.info(f"Normalized title to: {title}")
        elif "pages" in data.get("query", {}):
            page_id = next(iter(data["query"]["pages"]))
            if page_id != "-1":  # -1 indicates page not found
                title = data["query"]["pages"][page_id]["title"]
                logger.info(f"Found page title: {title}")
            else:
                logger.warning(f"Page not found: {title}")
                return None

        return title
    except Exception as e:
        logger.error(f"Error resolving redirect for {title}: {e}")
        return None

def get_wiki_id_from_page(page_title: str) -> Optional[str]:
    """Get Wikidata ID from Wikipedia page title.

    Args:
        page_title: Page URL title (end of URL)

    Returns:
        Wiki Data identifier or None if not found
    """
    if not page_title:
        return None

    try:
        # First try to resolve any redirects
        resolved_title = resolve_redirect(page_title)
        if not resolved_title:
            logger.warning(f"Could not resolve page title: {page_title}")
            return None

        logger.info(f"Getting Wikidata ID for page: {resolved_title}")
        params = {
            "action": "wbgetentities",
            "format": "json",
            "sites": "enwiki",
            "titles": resolved_title,
            "languages": "en",
            "redirects": "yes"
        }
        
        data = fetch_wikidata(params)
        if not data or "entities" not in data or not data["entities"]:
            logger.warning(f"No Wikidata entity found for page: {resolved_title}")
            return None

        entity_id = next(iter(data["entities"]))
        if entity_id == "-1":
            logger.warning(f"Invalid Wikidata entity for page: {resolved_title}")
            return None

        logger.info(f"Found Wikidata ID {entity_id} for page {resolved_title}")
        return entity_id
    except Exception as e:
        logger.error(f"Error getting Wiki ID for {page_title}: {e}")
        return None

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

    try:
        logger.info(f"Getting {wikidata_prop_id} for entity {wikidata_q_number}")
        params = {
            "action": "wbgetentities",
            "ids": wikidata_q_number,
            "format": "json",
            "languages": "en"
        }

        data = fetch_wikidata(params)
        if not data or "entities" not in data or wikidata_q_number not in data["entities"]:
            logger.warning(f"Invalid data for {wikidata_q_number}")
            return None

        claims = data["entities"][wikidata_q_number]["claims"]
        if wikidata_prop_id not in claims:
            logger.info(f"Property {wikidata_prop_id} not found for {wikidata_q_number}")
            return None

        date_str = claims[wikidata_prop_id][0]["mainsnak"]["datavalue"]["value"]["time"]
        logger.info(f"Found date {date_str} for {wikidata_prop_id} on {wikidata_q_number}")

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
            return date_obj
        except ValueError as e:
            logger.error(f"Error parsing date {date_str}: {e}")
            return None

    except Exception as e:
        logger.error(f"Error getting date for {wikidata_q_number}: {e}")
        return None

def calculate_age(birth_date: datetime, death_date: Optional[datetime] = None) -> int:
    """Calculate age based on birth date and optional death date."""
    if not birth_date:
        return 0

    end_date = death_date if death_date else datetime.now()
    age = end_date.year - birth_date.year

    # Adjust age if birthday hasn't occurred this year
    if (end_date.month, end_date.day) < (birth_date.month, birth_date.day):
        age -= 1

    return max(0, age)