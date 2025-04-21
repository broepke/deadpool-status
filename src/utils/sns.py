"""
SNS utilities for managing subscriptions and sending notifications
"""
import os
import boto3
import logging
from botocore.exceptions import ClientError
from typing import Optional

# Configure logging
logger = logging.getLogger()

def get_sns_topic_arn() -> Optional[str]:
    """Get the SNS topic ARN from environment variables or CloudFormation outputs"""
    # Try to get from environment variable first
    sns_topic_arn = os.environ.get('SNS_TOPIC_ARN')
    if sns_topic_arn:
        return sns_topic_arn
    
    # If not available, try to get from CloudFormation outputs
    try:
        cloudformation = boto3.client('cloudformation')
        response = cloudformation.describe_stacks(StackName='SmsQuickStartStack-43557177')
        
        for stack in response['Stacks']:
            for output in stack.get('Outputs', []):
                if output.get('OutputKey') == 'SNSArn':
                    return output.get('OutputValue')
    except ClientError as e:
        logger.error(f"Error getting stack outputs: {e}")
    
    return None

def manage_sns_subscription(phone_number: str, subscribe: bool = True) -> Optional[str]:
    """
    Subscribe or unsubscribe a phone number to/from the SNS topic
    
    Args:
        phone_number: Phone number to subscribe/unsubscribe
        subscribe: True to subscribe, False to unsubscribe
        
    Returns:
        Subscription ARN if subscribed, None otherwise
    """
    # Get SNS topic ARN
    sns_topic_arn = get_sns_topic_arn()
    if not sns_topic_arn:
        logger.error("SNS topic ARN not found")
        return None
    
    # Initialize SNS client
    sns = boto3.client('sns')
    
    try:
        # List existing subscriptions to find if the phone number is already subscribed
        existing_subscription = None
        paginator = sns.get_paginator('list_subscriptions_by_topic')
        for page in paginator.paginate(TopicArn=sns_topic_arn):
            for subscription in page.get('Subscriptions', []):
                if subscription.get('Protocol') == 'sms' and subscription.get('Endpoint') == phone_number:
                    existing_subscription = subscription.get('SubscriptionArn')
                    break
        
        # Subscribe or unsubscribe based on the flag
        if subscribe:
            if existing_subscription and existing_subscription != 'PendingConfirmation':
                logger.info(f"Phone number {phone_number} is already subscribed")
                return existing_subscription
            
            # Subscribe the phone number
            response = sns.subscribe(
                TopicArn=sns_topic_arn,
                Protocol='sms',
                Endpoint=phone_number
            )
            subscription_arn = response.get('SubscriptionArn')
            logger.info(f"Subscribed {phone_number} to SNS topic: {subscription_arn}")
            return subscription_arn
        else:
            # Unsubscribe if already subscribed
            if existing_subscription and existing_subscription != 'PendingConfirmation':
                sns.unsubscribe(SubscriptionArn=existing_subscription)
                logger.info(f"Unsubscribed {phone_number} from SNS topic")
            else:
                logger.info(f"Phone number {phone_number} is not subscribed")
            return None
    
    except ClientError as e:
        logger.error(f"Error managing SNS subscription: {e}")
        return None

def send_notification(message: str, attributes: dict = None) -> Optional[str]:
    """
    Send a notification to the SNS topic
    
    Args:
        message: Message to send
        attributes: Optional message attributes
        
    Returns:
        Message ID if sent successfully, None otherwise
    """
    # Get SNS topic ARN
    sns_topic_arn = get_sns_topic_arn()
    if not sns_topic_arn:
        logger.error("SNS topic ARN not found")
        return None
    
    # Initialize SNS client
    sns = boto3.client('sns')
    
    # Default attributes for SMS messages
    if attributes is None:
        attributes = {
            'AWS.SNS.SMS.SMSType': {
                'DataType': 'String',
                'StringValue': 'Transactional'
            }
        }
    
    try:
        # Publish the message to the SNS topic
        response = sns.publish(
            TopicArn=sns_topic_arn,
            Message=message,
            MessageAttributes=attributes
        )
        message_id = response.get('MessageId')
        logger.info(f"Sent notification with message ID: {message_id}")
        return message_id
    
    except ClientError as e:
        logger.error(f"Error sending notification: {e}")
        return None