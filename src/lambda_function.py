"""
AWS Lambda handler for updating person records with Wikipedia data
"""

import os
import json
import logging
import time
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
    format_date
)

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO'))

# Constants
BATCH_SIZE = int(os.environ.get('BATCH_SIZE', 10))
BIRTH_DATE_PROP = 'P569'
DEATH_DATE_PROP = 'P570'
WIKI_API_DELAY = 1  # Delay between Wikipedia API calls in seconds

def generate_wiki_page(name: str) -> str:
    """Generate a Wikipedia page name from a person's name.
    
    Args:
        name: Person's name
        
    Returns:
        Wikipedia page name (with underscores)
    """
    # Replace spaces with underscores and handle special characters
    return name.strip().replace(' ', '_')

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
    
    # Generate WikiPage from Name if not present
    if not wiki_page and name:
        wiki_page = generate_wiki_page(name)
        person['WikiPage'] = wiki_page
        logger.info("Generated WikiPage %s for %s", wiki_page, name)
    
    # Get Wiki ID if not present
    if not wiki_id and wiki_page:
        wiki_id = get_wiki_id_from_page(wiki_page)
        if wiki_id:
            person['WikiID'] = wiki_id
            logger.info("Found Wiki ID %s for %s", wiki_id, name)
        else:
            # If we can't find the ID with the generated page name,
            # try with variations of the name
            variations = [
                name.replace(' ', '_'),  # Basic underscore replacement
                ''.join(word.capitalize() for word in name.split()),  # CamelCase
                '_'.join(word.capitalize() for word in name.split())  # Title_Case
            ]
            for variant in variations:
                if variant != wiki_page:
                    logger.info("Trying variant %s for %s", variant, name)
                    wiki_id = get_wiki_id_from_page(variant)
                    if wiki_id:
                        person['WikiID'] = wiki_id
                        person['WikiPage'] = variant
                        logger.info("Found Wiki ID %s using variant %s", wiki_id, variant)
                        break
    
    if not wiki_id:
        logger.warning("No Wiki ID available for %s", name)
        return None
    
    # Get birth and death dates
    try:
        birth_date = get_birth_death_date(BIRTH_DATE_PROP, wiki_id)
        time.sleep(WIKI_API_DELAY)  # Rate limiting
        death_date = get_birth_death_date(DEATH_DATE_PROP, wiki_id)
        
        if birth_date:
            person['BirthDate'] = format_date(birth_date)
            
            # Calculate age
            age = calculate_age(birth_date, death_date)
            person['Age'] = age
            
            if death_date:
                person['DeathDate'] = format_date(death_date)
                logger.info("Found death date for %s: %s", name, format_date(death_date))
                
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
        logger.info(f"Batch complete: {len(updates)} updates ready")
        return batch_update_persons(updates)
    
    logger.info("Batch complete: no updates needed")
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
        # Process records in batches
        while True:
            persons = get_persons_without_death_date(BATCH_SIZE)
            if not persons:
                logger.info("No more persons to process")
                break
                
            total_processed += len(persons)
            success_count, failure_count = process_batch(persons)
            total_updated += success_count
            total_failed += failure_count
            
            logger.info(
                "Progress - Processed: %d, Updated: %d, Failed: %d",
                total_processed, total_updated, total_failed
            )
            
            # Break if we've processed all records or hit the time limit
            time_elapsed = (datetime.now() - start_time).total_seconds()
            if time_elapsed > 240:  # Leave 60s buffer in 5min timeout
                logger.warning("Time limit approaching, stopping processing")
                break
    
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