"""
DynamoDB utilities for person record operations
"""

import os
import logging
import hashlib
import boto3
from typing import List, Dict, Any, Optional
from datetime import datetime
from boto3.dynamodb.conditions import Key, Attr

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

def create_hash(person: Dict[str, Any]) -> str:
    """Create a hash of person data for change detection.

    Args:
        person: Person record dictionary

    Returns:
        MD5 hash of the person's data
    """
    # Extract relevant fields in a consistent order
    fields = [
        str(person.get('Name', '')),
        str(person.get('WikiPage', '')),
        str(person.get('WikiID', '')),
        str(person.get('Age', 0)),
        str(person.get('BirthDate', '')),
        str(person.get('DeathDate', ''))
    ]
    
    # Create hash of concatenated fields
    combined = ''.join(fields)
    return hashlib.md5(combined.encode()).hexdigest()

def get_persons_without_death_date(batch_size: int = 25) -> List[Dict[str, Any]]:
    """Query DynamoDB for person records without death dates.

    Args:
        batch_size: Number of records to fetch per batch

    Returns:
        List of person records
    """
    try:
        # Query for DETAILS records without DeathDate
        response = table.scan(
            FilterExpression=Attr('SK').eq('DETAILS') & Attr('DeathDate').not_exists(),
            Limit=batch_size
        )
        
        items = response.get('Items', [])
        logger.info("Found %d persons without death date", len(items))
        return items
    except Exception as e:
        logger.error("Error querying DynamoDB: %s", e)
        raise

def format_date(date_obj: Optional[datetime]) -> Optional[str]:
    """Format datetime object as ISO string for DynamoDB.

    Args:
        date_obj: Datetime object to format

    Returns:
        ISO formatted date string or None
    """
    return date_obj.strftime('%Y-%m-%d') if date_obj else None

def update_person(
    person_id: str,
    birth_date: Optional[datetime] = None,
    death_date: Optional[datetime] = None,
    age: Optional[int] = None,
    wiki_id: Optional[str] = None
) -> bool:
    """Update person record in DynamoDB.

    Args:
        person_id: Person's UUID (without PERSON# prefix)
        birth_date: Birth date to update
        death_date: Death date to update
        age: Age to update
        wiki_id: Wiki ID to update

    Returns:
        True if update successful, False otherwise
    """
    try:
        # Build update expression and attribute values
        update_expr = ['SET']
        expr_values = {}
        expr_names = {}
        
        if birth_date:
            update_expr.append('#bd = :bd')
            expr_values[':bd'] = format_date(birth_date)
            expr_names['#bd'] = 'BirthDate'
            
        if death_date:
            update_expr.append('#dd = :dd')
            expr_values[':dd'] = format_date(death_date)
            expr_names['#dd'] = 'DeathDate'
            
        if age is not None:
            update_expr.append('#age = :age')
            expr_values[':age'] = age
            expr_names['#age'] = 'Age'
            
        if wiki_id:
            update_expr.append('#wid = :wid')
            expr_values[':wid'] = wiki_id
            expr_names['#wid'] = 'WikiID'
            
        if not expr_values:
            logger.info("No updates required for person %s", person_id)
            return True
            
        # Construct final update expression
        update_expression = ' '.join(update_expr)
        
        # Perform update
        table.update_item(
            Key={
                'PK': f'PERSON#{person_id}',
                'SK': 'DETAILS'
            },
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expr_values,
            ExpressionAttributeNames=expr_names
        )
        
        logger.info("Successfully updated person %s", person_id)
        return True
        
    except Exception as e:
        logger.error("Error updating person %s: %s", person_id, e)
        return False

def batch_update_persons(updates: List[Dict[str, Any]]) -> tuple[int, int]:
    """Batch update multiple person records.

    Args:
        updates: List of person records to update

    Returns:
        Tuple of (success_count, failure_count)
    """
    success_count = 0
    failure_count = 0
    
    for update in updates:
        person_id = update.get('PK', '').replace('PERSON#', '')
        if not person_id:
            logger.error("Invalid person ID in update: %s", update)
            failure_count += 1
            continue
            
        success = update_person(
            person_id=person_id,
            birth_date=update.get('BirthDate'),
            death_date=update.get('DeathDate'),
            age=update.get('Age'),
            wiki_id=update.get('WikiID')
        )
        
        if success:
            success_count += 1
        else:
            failure_count += 1
            
    return success_count, failure_count