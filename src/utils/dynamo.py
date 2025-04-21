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

def get_persons_without_death_date(max_items: int = None, start_key: Dict[str, Any] = None) -> tuple[List[Dict[str, Any]], str]:
    """Get persons without death dates from DynamoDB using pagination.
    
    Args:
        max_items: Maximum number of items to retrieve (None for all)
        start_key: Exclusive start key for pagination (None for first page)
        
    Returns:
        Tuple of (list of person records, pagination token as string)
        The pagination token can be used for pagination in subsequent calls
    """
    try:
        # Get batch size from environment variable or use default
        batch_size = int(os.environ.get('SCAN_BATCH_SIZE', '100'))
        logger.info(f"Using scan batch size of {batch_size}")
        
        # Get all records that:
        # 1. Start with PERSON# in PK
        # 2. Have SK = DETAILS
        # 3. Don't have a DeathDate
        filter_expression = (
            'begins_with(PK, :pk_prefix) AND '
            'SK = :sk AND '
            'attribute_not_exists(DeathDate)'
        )
        expression_attr_values = {
            ':pk_prefix': 'PERSON#',
            ':sk': 'DETAILS'
        }
        
        # Initialize variables for pagination
        items = []
        last_evaluated_key = start_key
        page_count = 0
        
        # Paginate through results
        while True:
            page_count += 1
            logger.info(f"Scanning page {page_count}")
            
            # Prepare scan parameters
            scan_params = {
                'FilterExpression': filter_expression,
                'ExpressionAttributeValues': expression_attr_values,
                'Limit': batch_size
            }
            
            # Add ExclusiveStartKey for pagination if we have one
            if last_evaluated_key:
                scan_params['ExclusiveStartKey'] = last_evaluated_key
                logger.info(f"Using start key: {json.dumps(last_evaluated_key, default=str)}")
            
            # Execute the scan
            response = table.scan(**scan_params)
            
            # Get items from this page
            page_items = response.get('Items', [])
            items.extend(page_items)
            logger.info(f"Retrieved {len(page_items)} persons on page {page_count}")
            
            # Check if we've reached the maximum number of items
            if max_items and len(items) >= max_items:
                logger.info(f"Reached maximum item limit of {max_items}")
                items = items[:max_items]  # Trim to max_items
                break
            
            # Check if there are more pages
            last_evaluated_key = response.get('LastEvaluatedKey')
            if not last_evaluated_key:
                logger.info(f"No more pages to scan")
                break
            
            # If we have a max_items limit and we've reached it, stop pagination
            if max_items and len(items) >= max_items:
                break
        
        logger.info(f"Retrieved a total of {len(items)} persons to process")
        
        # Log a sample of records for debugging (first 5)
        for i, item in enumerate(items[:5]):
            logger.info(f"Sample record {i+1}: {json.dumps(item, default=str)}")
        
        # Convert the last_evaluated_key to a simple string token if it exists
        pagination_token = None
        if last_evaluated_key:
            # Use the PK as the pagination token since it's unique
            if 'PK' in last_evaluated_key:
                pagination_token = last_evaluated_key['PK']
                logger.info(f"Created pagination token from PK: {pagination_token}")
            else:
                # Fallback to using the whole key as JSON
                pagination_token = json.dumps(last_evaluated_key, default=str)
                logger.info(f"Created pagination token from full key: {pagination_token}")
            
        return items, pagination_token
    except Exception as e:
        logger.error(f"Error scanning table: {e}")
        return [], None

def prepare_person_for_update(person: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare a person record for DynamoDB update.
    
    Args:
        person: Person record to prepare
        
    Returns:
        Prepared person record
    """
    # Make a copy to avoid modifying the original
    person_copy = person.copy()
    
    # Ensure SK is DETAILS
    person_copy['SK'] = 'DETAILS'
    
    # If we have a Name but no WikiPage, generate it
    if 'Name' in person_copy and 'WikiPage' not in person_copy:
        person_copy['WikiPage'] = person_copy['Name'].replace(' ', '_')
        logger.info(f"Generated WikiPage {person_copy['WikiPage']} for {person_copy['Name']}")
    
    # Convert datetime objects to string dates
    if 'BirthDate' in person_copy and isinstance(person_copy['BirthDate'], datetime):
        person_copy['BirthDate'] = format_date(person_copy['BirthDate'])
    if 'DeathDate' in person_copy and isinstance(person_copy['DeathDate'], datetime):
        person_copy['DeathDate'] = format_date(person_copy['DeathDate'])
    
    return person_copy

def batch_update_persons(persons: List[Dict[str, Any]], max_batch_size: int = 25) -> tuple[int, int]:
    """Update multiple person records in DynamoDB using batch operations.
    
    Args:
        persons: List of person records to update
        max_batch_size: Maximum number of items in a single batch write (DynamoDB limit is 25)
        
    Returns:
        Tuple of (success_count, failure_count)
    """
    success_count = 0
    failure_count = 0
    
    # Process in chunks of max_batch_size
    for i in range(0, len(persons), max_batch_size):
        chunk = persons[i:i + max_batch_size]
        batch_items = []
        
        # Prepare each person for update
        for person in chunk:
            try:
                prepared_person = prepare_person_for_update(person)
                batch_items.append({
                    'PutRequest': {
                        'Item': prepared_person
                    }
                })
                logger.debug(f"Prepared {prepared_person.get('Name', 'Unknown')} for batch update")
            except Exception as e:
                logger.error(f"Error preparing person {person.get('Name', 'Unknown')} for batch update: {e}")
                failure_count += 1
        
        # Skip if no items to update
        if not batch_items:
            continue
        
        # Perform batch write
        try:
            logger.info(f"Performing batch write with {len(batch_items)} items")
            
            # DynamoDB batch_write_item requires a dict with table name as key
            response = dynamodb.batch_write_item(
                RequestItems={
                    os.environ['TABLE_NAME']: batch_items
                }
            )
            
            # Check for unprocessed items
            unprocessed = response.get('UnprocessedItems', {}).get(os.environ['TABLE_NAME'], [])
            if unprocessed:
                logger.warning(f"{len(unprocessed)} items were not processed in batch")
                
                # Try to process unprocessed items individually
                for item in unprocessed:
                    try:
                        put_request = item.get('PutRequest', {})
                        if put_request and 'Item' in put_request:
                            table.put_item(Item=put_request['Item'])
                            success_count += 1
                            logger.info(f"Successfully processed unprocessed item individually")
                    except Exception as e:
                        logger.error(f"Error processing unprocessed item: {e}")
                        failure_count += 1
            
            # Count successful updates
            success_count += len(batch_items) - len(unprocessed)
            
        except Exception as e:
            logger.error(f"Error performing batch write: {e}")
            
            # Try to process items individually on batch failure
            logger.info(f"Attempting to process {len(batch_items)} items individually after batch failure")
            for item in batch_items:
                try:
                    put_request = item.get('PutRequest', {})
                    if put_request and 'Item' in put_request:
                        table.put_item(Item=put_request['Item'])
                        success_count += 1
                except Exception as individual_error:
                    logger.error(f"Error updating person individually: {individual_error}")
                    failure_count += 1
    
    logger.info(f"Batch update complete: {success_count} succeeded, {failure_count} failed")
    return success_count, failure_count
