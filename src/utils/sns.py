"""
AWS SNS utilities for sending notifications and managing subscriptions
"""

import os
import boto3
import logging
from typing import Optional

logger = logging.getLogger()

def get_sns_topic_arn() -> str:
    """Get the SNS topic ARN from environment variables"""
    return os.environ.get('SNS_TOPIC_ARN')

def clean_phone_number(phone: str) -> str:
    """Clean phone number by removing all non-standard characters
    
    Args:
        phone: Phone number to clean
        
    Returns:
        Cleaned phone number with only + and digits
    """
    # Keep only +, digits, and standard ASCII characters
    cleaned = ''
    for char in phone:
        if char == '+' or char.isdigit():
            cleaned += char
    return cleaned

def manage_sns_subscription(phone_number: str, enable: bool = True) -> Optional[str]:
    """Manage SNS topic subscription based on SMS notification preference
    
    Args:
        phone_number: Phone number to manage subscription for
        enable: True to subscribe, False to unsubscribe
        
    Returns:
        SubscriptionArn if subscribed, None otherwise
    """
    # Clean the phone number to remove any hidden Unicode characters
    cleaned_phone = clean_phone_number(phone_number)
    if cleaned_phone != phone_number:
        logger.info("Cleaned phone number from %s to %s", phone_number, cleaned_phone)
        phone_number = cleaned_phone
    
    sns = boto3.client('sns')
    topic_arn = get_sns_topic_arn()
    
    if not topic_arn:
        logger.warning("SNS_TOPIC_ARN not configured")
        return None
        
    try:
        # Get current subscriptions
        subscriptions = sns.list_subscriptions_by_topic(TopicArn=topic_arn)
        existing_sub = None
        
        # Check if phone number is already subscribed
        for sub in subscriptions.get('Subscriptions', []):
            if sub.get('Endpoint') == phone_number:
                existing_sub = sub
                break
        
        if enable:
            if not existing_sub:
                # Subscribe if enabling and not already subscribed
                response = sns.subscribe(
                    TopicArn=topic_arn,
                    Protocol='sms',
                    Endpoint=phone_number
                )
                logger.info("Subscribed %s to notifications", phone_number)
                return response['SubscriptionArn']
            else:
                logger.info("Phone number %s already subscribed", phone_number)
                return existing_sub['SubscriptionArn']
        else:
            if existing_sub:
                # Unsubscribe if disabling and currently subscribed
                sns.unsubscribe(
                    SubscriptionArn=existing_sub['SubscriptionArn']
                )
                logger.info("Unsubscribed %s from notifications", phone_number)
            else:
                logger.info("Phone number %s not currently subscribed", phone_number)
                
        return None
                
    except Exception as e:
        logger.error("Failed to manage notification subscription for %s: %s", 
                    phone_number, str(e))
        raise

def send_verification_code(phone_number: str, code: str) -> str:
    """Send verification code via SNS
    
    Args:
        phone_number: Phone number to send code to
        code: Verification code to send
        
    Returns:
        MessageId of sent message
    """
    # Clean the phone number to remove any hidden Unicode characters
    cleaned_phone = clean_phone_number(phone_number)
    if cleaned_phone != phone_number:
        logger.info("Cleaned phone number from %s to %s", phone_number, cleaned_phone)
        phone_number = cleaned_phone
        
    sns = boto3.client('sns')
    
    try:
        response = sns.publish(
            PhoneNumber=phone_number,
            Message=f"Your Deadpool Game verification code is: {code}",
            MessageAttributes={
                'AWS.SNS.SMS.SMSType': {
                    'DataType': 'String',
                    'StringValue': 'Transactional'
                }
            }
        )
        logger.info("Sent verification code to %s", phone_number)
        return response['MessageId']
    except Exception as e:
        logger.error("Failed to send verification code to %s: %s", 
                    phone_number, str(e))
        raise

def send_death_notification(person_name: str, death_date: str) -> None:
    """Send SMS notification about a person's death
    
    Args:
        person_name: Name of the person who died
        death_date: Date of death in ISO format
    """
    sns = boto3.client('sns')
    topic_arn = get_sns_topic_arn()
    
    if not topic_arn:
        logger.warning("SNS_TOPIC_ARN not configured, skipping notifications")
        return
        
    try:
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
            "Death notification sent for %s. MessageId: %s",
            person_name,
            response['MessageId']
        )
        
    except Exception as e:
        logger.error("Failed to send death notification: %s", str(e))
        raise