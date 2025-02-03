"""
AWS SNS utilities for sending notifications
"""

import os
import boto3
import logging
from typing import Dict, Any, List

logger = logging.getLogger()

def get_users_for_notification() -> List[Dict[str, Any]]:
    """Get all users who have opted into SMS notifications"""
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(os.environ['TABLE_NAME'])
    
    response = table.query(
        IndexName='SK-PK-index',
        KeyConditionExpression='SK = :sk',
        FilterExpression='SmsNotificationsEnabled = :enabled AND PhoneVerified = :verified',
        ExpressionAttributeValues={
            ':sk': 'DETAILS',
            ':enabled': True,
            ':verified': True
        }
    )
    
    return response.get('Items', [])

def send_death_notification(person_name: str, death_date: str) -> None:
    """Send SMS notification about a person's death
    
    Args:
        person_name: Name of the person who died
        death_date: Date of death in ISO format
    """
    sns = boto3.client('sns')
    topic_arn = os.environ.get('SNS_TOPIC_ARN')
    
    if not topic_arn:
        logger.warning("SNS_TOPIC_ARN not configured, skipping notifications")
        return
        
    try:
        # Get users who should receive notifications
        users = get_users_for_notification()
        
        if not users:
            logger.info("No users opted in for notifications")
            return
            
        # Format the message
        message = f"🎯 {person_name} has passed away on {death_date}. Check the game for updates!"
        
        # Publish to SNS topic
        response = sns.publish(
            TopicArn=topic_arn,
            Message=message,
            MessageAttributes={
                'AWS.SNS.SMS.SMSType': {
                    'DataType': 'String',
                    'StringValue': 'Transactional'
                }
            }
        )
        
        logger.info(
            "Death notification sent for %s to %d users. MessageId: %s",
            person_name,
            len(users),
            response['MessageId']
        )
        
    except Exception as e:
        logger.error("Failed to send death notification: %s", str(e))
        raise