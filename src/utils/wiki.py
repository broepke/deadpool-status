"""
Mock Wikipedia/Wikidata utilities for local testing
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Mock data for testing
MOCK_WIKI_DATA = {
    'Q12345': {
        'birth_date': datetime(1950, 1, 1),
        'death_date': datetime(2023, 12, 31)
    },
    'Q67890': {
        'birth_date': datetime(1960, 6, 15),
        'death_date': None
    }
}

def get_wiki_id_from_page(page_title: str) -> Optional[str]:
    """Mock getting Wikidata ID from Wikipedia page title."""
    # Simple mock that returns Q numbers based on page title
    if page_title == 'Test_Person_1':
        return 'Q12345'
    elif page_title == 'Test_Person_2':
        return 'Q67890'
    return None

def get_birth_death_date(wikidata_prop_id: str, wikidata_q_number: str) -> Optional[datetime]:
    """Mock getting birth or death date from Wikidata."""
    if wikidata_q_number not in MOCK_WIKI_DATA:
        return None
        
    person_data = MOCK_WIKI_DATA[wikidata_q_number]
    
    if wikidata_prop_id == 'P569':  # Birth date
        return person_data['birth_date']
    elif wikidata_prop_id == 'P570':  # Death date
        return person_data['death_date']
    
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