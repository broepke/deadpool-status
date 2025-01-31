"""
DynamoDB utilities for person record management
"""
import json
import os
import logging
import boto3
from datetime import datetime
from typing import Dict, Any, List

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

# Configure logging
logger = logging.getLogger()

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def format_date(dt: datetime) -> str:
    """Format datetime to YYYY-MM-DD string."""
    return dt.strftime('%Y-%m-%d')

def get_persons_without_death_date() -> List[Dict[str, Any]]:
    """Get all persons without death dates from DynamoDB.
    
    Returns:
        List of person records
    """
    try:
        # Get all records that:
        # 1. Start with PERSON# in PK
        # 2. Have SK = DETAILS
        # 3. Don't have a DeathDate
        response = table.scan(
            FilterExpression=(
                'begins_with(PK, :pk_prefix) AND '
                'SK = :sk AND '
                'attribute_not_exists(DeathDate)'
            ),
            ExpressionAttributeValues={
                ':pk_prefix': 'PERSON#',
                ':sk': 'DETAILS'
            }
        )
        
        items = response.get('Items', [])
        logger.info(f"Retrieved {len(items)} persons to process")
        
        # Log each record for debugging
        for item in items:
            logger.info(f"Retrieved record: {json.dumps(item, default=str)}")
            
        return items
    except Exception as e:
        logger.error(f"Error scanning table: {e}")
        return []

def batch_update_persons(persons: List[Dict[str, Any]]) -> tuple[int, int]:
    """Update multiple person records in DynamoDB.
    
    Args:
        persons: List of person records to update
        
    Returns:
        Tuple of (success_count, failure_count)
    """
    success_count = 0
    failure_count = 0
    
    for person in persons:
        try:
            # Ensure SK is DETAILS
            person['SK'] = 'DETAILS'
            
            # If we have a Name but no WikiPage, generate it
            if 'Name' in person and 'WikiPage' not in person:
                person['WikiPage'] = person['Name'].replace(' ', '_')
                logger.info(f"Generated WikiPage {person['WikiPage']} for {person['Name']}")
            
            # Convert datetime objects to string dates
            if 'BirthDate' in person and isinstance(person['BirthDate'], datetime):
                person['BirthDate'] = format_date(person['BirthDate'])
            if 'DeathDate' in person and isinstance(person['DeathDate'], datetime):
                person['DeathDate'] = format_date(person['DeathDate'])
            
            logger.info(f"Updating person: {json.dumps(person, default=str)}")
            table.put_item(Item=person)
            success_count += 1
            
        except Exception as e:
            logger.error(f"Error updating person {person.get('Name', 'Unknown')}: {e}")
            failure_count += 1
    
    logger.info(f"Batch update complete: {success_count} succeeded, {failure_count} failed")
    return success_count, failure_count
