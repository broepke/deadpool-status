"""
AWS Lambda handler for updating person records with Wikipedia data
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

from utils.wiki import (
    get_wiki_id_from_page,
    get_birth_death_date,
    calculate_age
)
from utils.dynamo import (
    get_persons_without_death_date,
    batch_update_persons,
    create_hash,
    DateTimeEncoder
)

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# Constants
BATCH_SIZE = int(os.environ.get('BATCH_SIZE', 25))
BIRTH_DATE_PROP = 'P569'
DEATH_DATE_PROP = 'P570'

def process_person(person: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single person record.

    Args:
        person: Person record from DynamoDB

    Returns:
        Updated person record if changes needed, None if no changes
    """
    person_id = person['PK'].replace('PERSON#', '')
    name = person.get('Name', '')
    wiki_page = person.get('WikiPage')
    wiki_id = person.get('WikiID')
    
    logger.info("Processing person: %s (ID: %s)", name, person_id)
    
    # Create hash of current data
    original_hash = create_hash(person)
    
    # Get Wiki ID if not present
    if not wiki_id and wiki_page:
        wiki_id = get_wiki_id_from_page(wiki_page)
        if wiki_id:
            person['WikiID'] = wiki_id
            logger.info("Found Wiki ID %s for %s", wiki_id, name)
    
    if not wiki_id:
        logger.warning("No Wiki ID available for %s", name)
        return None
    
    # Get birth and death dates
    try:
        birth_date = get_birth_death_date(BIRTH_DATE_PROP, wiki_id)
        death_date = get_birth_death_date(DEATH_DATE_PROP, wiki_id)
        
        if birth_date:
            person['BirthDate'] = birth_date
            
            # Calculate age
            age = calculate_age(birth_date, death_date)
            person['Age'] = age
            
            if death_date:
                person['DeathDate'] = death_date
                logger.info("Found death date for %s: %s", name, death_date)
                
    except Exception as e:
        logger.error("Error processing dates for %s: %s", name, e)
        return None
    
    # Check if any data changed
    new_hash = create_hash(person)
    if new_hash != original_hash:
        logger.info("Changes detected for %s", name)
        return person
    
    logger.info("No changes needed for %s", name)
    return None

def process_batch(persons: List[Dict[str, Any]]) -> tuple[int, int]:
    """Process a batch of person records.

    Args:
        persons: List of person records to process

    Returns:
        Tuple of (success_count, failure_count)
    """
    updates = []
    
    for person in persons:
        try:
            updated_person = process_person(person)
            if updated_person:
                updates.append(updated_person)
        except Exception as e:
            logger.error("Error processing person %s: %s", 
                        person.get('Name', 'Unknown'), e)
    
    if updates:
        return batch_update_persons(updates)
    return 0, 0

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AWS Lambda handler function.

    Args:
        event: Lambda event data
        context: Lambda context object

    Returns:
        Response dictionary with processing results
    """
    start_time = datetime.now()
    total_processed = 0
    total_updated = 0
    total_failed = 0
    
    try:
        # When running locally, just process one batch
        is_local = hasattr(context, 'log_stream_name') and context.log_stream_name == 'local'
        
        while True:
            persons = get_persons_without_death_date(BATCH_SIZE)
            if not persons:
                break
                
            total_processed += len(persons)
            success_count, failure_count = process_batch(persons)
            total_updated += success_count
            total_failed += failure_count
            
            # Break if running locally or hit time limit
            if is_local or (datetime.now() - start_time).total_seconds() > 240:
                break
    
    except Exception as e:
        logger.error("Error in main processing loop: %s", e)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'processed': total_processed,
                'updated': total_updated,
                'failed': total_failed
            }, cls=DateTimeEncoder)
        }
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'processed': total_processed,
            'updated': total_updated,
            'failed': total_failed,
            'duration': (datetime.now() - start_time).total_seconds()
        }, cls=DateTimeEncoder)
    }