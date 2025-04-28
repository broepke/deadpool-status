"""
AWS Lambda handler for updating person records with Wikipedia data
"""

import os
import json
import logging
import time
import random
import boto3
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

# Custom JSON encoder for serializing non-standard types
class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, bytes):
            return obj.decode('utf-8')
        return json.JSONEncoder.default(self, obj)

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

def process_records(persons: List[Dict[str, Any]], batch_size: int = 10) -> tuple[int, int]:
    """Process a list of person records in batches.

    Args:
        persons: List of person records to process
        batch_size: Number of records to process in each batch

    Returns:
        Tuple of (success_count, failure_count)
    """
    total_success = 0
    total_failure = 0
    updates = []
    
    # Process in batches to avoid rate limiting
    for i in range(0, len(persons), batch_size):
        batch = persons[i:i+batch_size]
        batch_number = (i // batch_size) + 1
        total_batches = (len(persons) + batch_size - 1) // batch_size
        
        logger.info(f"Processing batch {batch_number}/{total_batches} ({len(batch)} records)")
        
        # Add a delay between batches to avoid rate limiting
        if i > 0:
            delay = random.uniform(2.0, 5.0)
            logger.info(f"Pausing for {delay:.2f} seconds between batches")
            time.sleep(delay)
        
        # Process each person in the batch
        batch_updates = []
        for person in batch:
            try:
                updated_person = process_person(person)
                if updated_person:
                    batch_updates.append(updated_person)
                    updates.append(updated_person)
            except Exception as e:
                logger.error("Error processing person %s: %s",
                            person.get('Name', 'Unknown'), e)
        
        # Update DynamoDB with batch results
        if batch_updates:
            logger.info(f"Batch {batch_number} complete: {len(batch_updates)} updates ready")
            success, failure = batch_update_persons(batch_updates)
            total_success += success
            total_failure += failure
            
            # Log progress
            logger.info(
                f"Progress - Batch: {batch_number}/{total_batches}, "
                f"Processed: {len(batch)}, Updated: {success}, Failed: {failure}, "
                f"Running Total - Updated: {total_success}, Failed: {total_failure}"
            )
        else:
            logger.info(f"Batch {batch_number} complete: no updates needed")
    
    if updates:
        logger.info(f"All batches complete: {len(updates)} total updates processed")
    else:
        logger.info("All batches complete: no updates needed")
        
    return total_success, total_failure

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
    
    # Get batch size from environment variable or use default
    batch_size = int(os.environ.get('BATCH_SIZE', '10'))
    logger.info(f"Using batch size of {batch_size}")
    
    # Check if this is a continuation of a previous run
    start_key = None
    
    # Extract pagination token from event if present
    if event and isinstance(event, dict):
        body = event.get('body')
        if body and isinstance(body, str):
            try:
                body_json = json.loads(body)
                if isinstance(body_json, dict):
                    token = body_json.get('paginationToken')
                    if token:
                        # Convert string token to DynamoDB key
                        if isinstance(token, str):
                            if token.startswith(('PERSON#', 'PLAYER#')):
                                # It's a PK, create a proper key
                                start_key = {'PK': token, 'SK': 'DETAILS'}
                                logger.info(f"Created proper key from PK: {start_key}")
                            else:
                                # Try to parse it as JSON
                                try:
                                    start_key = json.loads(token)
                                    logger.info(f"Parsed token as JSON: {start_key}")
                                except Exception as e:
                                    logger.error(f"Failed to parse token as JSON: {e}")
                                    # Use as is
                                    start_key = token
                        else:
                            start_key = token
                        
                        logger.info(f"Continuing from pagination token: {token}")
            except json.JSONDecodeError:
                pass
        elif isinstance(event, dict):
            token = event.get('paginationToken')
            if token:
                # Convert string token to DynamoDB key
                if isinstance(token, str):
                    if token.startswith(('PERSON#', 'PLAYER#')):
                        # It's a PK, create a proper key
                        start_key = {'PK': token, 'SK': 'DETAILS'}
                        logger.info(f"Created proper key from PK: {start_key}")
                    else:
                        # Try to parse it as JSON
                        try:
                            start_key = json.loads(token)
                            logger.info(f"Parsed token as JSON: {start_key}")
                        except Exception as e:
                            logger.error(f"Failed to parse token as JSON: {e}")
                            # Use as is
                            start_key = token
                else:
                    start_key = token
                
                logger.info(f"Continuing from pagination token: {token}")
    
    try:
        # Get records that need processing, with a limit to prevent timeouts
        max_items = int(os.environ.get('MAX_ITEMS_PER_RUN', '100'))
        logger.info(f"Using maximum of {max_items} items per run")
        
        # Get records with pagination
        persons, next_token = get_persons_without_death_date(max_items=max_items, start_key=start_key)
        
        if persons:
            total_processed = len(persons)
            logger.info(f"Retrieved {total_processed} records to process")
            
            # Process records in batches
            success_count, failure_count = process_records(persons, batch_size)
            total_updated = success_count
            total_failed = failure_count
            
            logger.info(
                "Final Summary - Processed: %d, Updated: %d, Failed: %d",
                total_processed, total_updated, total_failed
            )
        else:
            logger.info("No records to process")
    
    except Exception as e:
        logger.error("Error in main processing loop: %s", e)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'processed': total_processed,
                'updated': total_updated,
                'failed': total_failed,
                'duration': (datetime.now() - start_time).total_seconds(),
                'hasMoreRecords': next_token is not None,
                'paginationToken': next_token
            })
        }
    
    duration = (datetime.now() - start_time).total_seconds()
    logger.info(
        "Execution complete - Duration: %.2fs, Processed: %d, Updated: %d, Failed: %d",
        duration, total_processed, total_updated, total_failed
    )
    
    # Check if there are more records to process
    has_more = next_token is not None
    if has_more:
        logger.info(f"More records available. Next pagination token: {json.dumps(next_token, default=str)}")
        
        # Check if we should self-invoke to process the next batch
        auto_paginate = os.environ.get('AUTO_PAGINATE', 'false').lower() == 'true'
        invocation_count = int(event.get('invocationCount', 0)) + 1
        max_invocations = int(os.environ.get('MAX_AUTO_INVOCATIONS', '10'))
        running_total_processed = int(event.get('runningTotalProcessed', 0)) + total_processed
        running_total_updated = int(event.get('runningTotalUpdated', 0)) + total_updated
        running_total_failed = int(event.get('runningTotalFailed', 0)) + total_failed
        
        if auto_paginate and invocation_count < max_invocations:
            logger.info(f"Auto-pagination enabled. Self-invoking for next batch. Invocation {invocation_count}/{max_invocations}")
            
            # Create payload for next invocation
            payload = {
                'paginationToken': next_token,
                'invocationCount': invocation_count,
                'runningTotalProcessed': running_total_processed,
                'runningTotalUpdated': running_total_updated,
                'runningTotalFailed': running_total_failed
            }
            
            try:
                # Get the function name from the context or environment
                function_name = context.function_name
                
                # Create Lambda client
                lambda_client = boto3.client('lambda')
                
                # Invoke the function asynchronously
                response = lambda_client.invoke(
                    FunctionName=function_name,
                    InvocationType='Event',  # Asynchronous invocation
                    Payload=json.dumps(payload)
                )
                
                status_code = response.get('StatusCode')
                logger.info(f"Successfully invoked next batch processing with pagination token. Status code: {status_code}")
            except Exception as e:
                logger.error(f"Error invoking next batch: {e}")
        else:
            if not auto_paginate:
                logger.info("Auto-pagination disabled. Not self-invoking for next batch.")
            elif invocation_count >= max_invocations:
                logger.info(f"Reached maximum auto-invocations ({max_invocations}). Not self-invoking for next batch.")
    else:
        logger.info("All records processed. No more records available.")
    
    # Prepare response
    response = {
        'statusCode': 200,
        'body': json.dumps({
            'processed': total_processed,
            'updated': total_updated,
            'failed': total_failed,
            'duration': duration,
            'hasMoreRecords': has_more,
            'invocationCount': event.get('invocationCount', 0) + 1,
            'runningTotalProcessed': running_total_processed if has_more else total_processed,
            'runningTotalUpdated': running_total_updated if has_more else total_updated,
            'runningTotalFailed': running_total_failed if has_more else total_failed
        })
    }
    
    # Add pagination token if there are more records
    if has_more:
        response['body'] = json.dumps({
            'processed': total_processed,
            'updated': total_updated,
            'failed': total_failed,
            'duration': duration,
            'hasMoreRecords': True,
            'paginationToken': next_token,
            'invocationCount': event.get('invocationCount', 0) + 1,
            'runningTotalProcessed': running_total_processed,
            'runningTotalUpdated': running_total_updated,
            'runningTotalFailed': running_total_failed
        })
    
    return response