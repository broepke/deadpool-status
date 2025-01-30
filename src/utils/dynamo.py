"""
DynamoDB utilities for person record management
"""
import hashlib
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

def format_date(dt: datetime) -> str:
    """Format datetime to YYYY-MM-DD string."""
    return dt.strftime('%Y-%m-%d')

def get_persons_without_death_date(batch_size: int) -> List[Dict[str, Any]]:
    """Get persons without death dates from DynamoDB.
    
    Args:
        batch_size: Number of records to fetch
        
    Returns:
        List of person records
    """
    try:
        # Get records that either:
        # 1. Don't have WikiID (new records)
        # 2. Have WikiID but no DeathDate (existing records to check)
        scan_kwargs = {
            'FilterExpression': '(attribute_not_exists(WikiID) OR (attribute_exists(WikiID) AND attribute_not_exists(DeathDate))) AND begins_with(PK, :pk_prefix) AND SK = :sk_value',
            'ExpressionAttributeValues': {
                ':pk_prefix': 'PERSON#',
                ':sk_value': 'DETAILS'
            },
            'Limit': batch_size
        }

        done = False
        start_key = None
        items = []

        while not done and len(items) < batch_size:
            if start_key:
                scan_kwargs['ExclusiveStartKey'] = start_key
            
            response = table.scan(**scan_kwargs)
            items.extend(response.get('Items', []))
            
            # Paginate only if we need more items
            if len(items) < batch_size and 'LastEvaluatedKey' in response:
                start_key = response['LastEvaluatedKey']
            else:
                done = True

        items = items[:batch_size]  # Ensure we don't return more than batch_size
        
        for item in items:
            logger.info(f"Retrieved record: {json.dumps(item, default=str)}")
        
        logger.info(f"Retrieved {len(items)} persons to process")
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
            
            logger.info(f"Updating person: {json.dumps(person, default=str)}")
            table.put_item(Item=person)
            success_count += 1
            
        except Exception as e:
            logger.error(f"Error updating person {person.get('Name', 'Unknown')}: {e}")
            failure_count += 1
    
    logger.info(f"Batch update complete: {success_count} succeeded, {failure_count} failed")
    return success_count, failure_count

def create_hash(data: Dict[str, Any]) -> str:
    """Create a hash of the data for change detection."""
    # Create a copy of the data without dates for hashing
    hash_data = data.copy()
    # Remove fields that change frequently
    for field in ['Age', 'BirthDate', 'DeathDate']:
        hash_data.pop(field, None)
    
    serialized = json.dumps(hash_data, sort_keys=True)
    return hashlib.md5(serialized.encode()).hexdigest()