"""
Mock DynamoDB utilities for local testing
"""
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, List

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# Mock data for testing
MOCK_PERSONS = [
    {
        'PK': 'PERSON#1',
        'Name': 'Test Person 1',
        'WikiPage': 'Test_Person_1',
        'WikiID': 'Q12345'
    },
    {
        'PK': 'PERSON#2',
        'Name': 'Test Person 2',
        'WikiPage': 'Test_Person_2',
        'WikiID': 'Q67890'
    }
]

def get_persons_without_death_date(batch_size: int) -> List[Dict[str, Any]]:
    """Mock getting persons without death dates."""
    return MOCK_PERSONS[:batch_size]

def batch_update_persons(persons: List[Dict[str, Any]]) -> tuple[int, int]:
    """Mock updating persons in DynamoDB."""
    print(f"Would update {len(persons)} persons:")
    for person in persons:
        print(f"- {person['Name']}: {json.dumps(person, indent=2, cls=DateTimeEncoder)}")
    return len(persons), 0

def create_hash(data: Dict[str, Any]) -> str:
    """Create a hash of the data for change detection."""
    # Sort keys and handle datetime serialization
    serialized = json.dumps(data, sort_keys=True, cls=DateTimeEncoder)
    return hashlib.md5(serialized.encode()).hexdigest()