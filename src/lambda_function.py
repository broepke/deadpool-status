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
    format_date
)

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# Constants
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
    current_age = person.get('Age')
    
    logger.info("Processing person: %s (ID: %s)", name, person_id)
    logger.info("Current data: %s", json.dumps(person, default=str))
    
    # Generate WikiPage if not present
    if not wiki_page and name:
        wiki_page = name.replace(' ', '_')
        person['WikiPage'] = wiki_page
        logger.info("Generated WikiPage %s for %s", wiki_page, name)
    
    # Get Wiki ID if not present
    if not wiki_id and wiki_page:
        wiki_id = get_wiki_id_from_page(wiki_page)
        if wiki_id:
            person['WikiID'] = wiki_id
            logger.info("Found Wiki ID %s for %s", wiki_id, name)
    
    if not wiki_id:
        logger.warning("No Wiki ID available for %s (WikiPage: %s)", name, wiki_page)
        return None
    
    # Get birth and death dates
    try:
        birth_date = get_birth_death_date(BIRTH_DATE_PROP, wiki_id)
        death_date = get_birth_death_date(DEATH_DATE_PROP, wiki_id)
        
        needs_update = False
        
        if birth_date:
            new_birth_date = format_date(birth_date)
            if person.get('BirthDate') != new_birth_date:
                person['BirthDate'] = new_birth_date
                logger.info("Updated birth date to %s for %s", new_birth_date, name)
                needs_update = True
        
        if death_date:
            new_death_date = format_date(death_date)
            if person.get('DeathDate') != new_death_date:
                person['DeathDate'] = new_death_date
                logger.info("Found death date %s for %s", new_death_date, name)
                needs_update = True
            
        # Calculate age
        if birth_date:
            new_age = calculate_age(birth_date, death_date)
            if str(current_age) != str(new_age):  # Compare as strings since DynamoDB stores numbers as strings
                person['Age'] = new_age
                logger.info("Updated age from %s to %d for %s", current_age, new_age, name)
                needs_update = True
                
        if needs_update:
            logger.info("Changes detected for %s. Updated data: %s", name, json.dumps(person, default=str))
            return person
    
    except Exception as e:
        logger.error("Error processing dates for %s: %s", name, e)
        return None
    
    logger.info("No changes needed for %s", name)
    return None

def process_records(persons: List[Dict[str, Any]]) -> tuple[int, int]:
    """Process a list of person records.

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
        logger.info(f"Processing complete: {len(updates)} updates ready")
        return batch_update_persons(updates)
    
    logger.info("Processing complete: no updates needed")
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
        # Get all records that need processing
        persons = get_persons_without_death_date()
        if persons:
            total_processed = len(persons)
            success_count, failure_count = process_records(persons)
            total_updated = success_count
            total_failed = failure_count
            
            logger.info(
                "Progress - Processed: %d, Updated: %d, Failed: %d",
                total_processed, total_updated, total_failed
            )
    
    except Exception as e:
        logger.error("Error in main processing loop: %s", e)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'processed': total_processed,
                'updated': total_updated,
                'failed': total_failed,
                'duration': (datetime.now() - start_time).total_seconds()
            })
        }
    
    duration = (datetime.now() - start_time).total_seconds()
    logger.info(
        "Execution complete - Duration: %.2fs, Processed: %d, Updated: %d, Failed: %d",
        duration, total_processed, total_updated, total_failed
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'processed': total_processed,
            'updated': total_updated,
            'failed': total_failed,
            'duration': duration
        })
    }