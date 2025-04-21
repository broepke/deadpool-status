#!/usr/bin/env python3
import sys
import os
import boto3
import json
from botocore.exceptions import ClientError

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from utils.sns import manage_sns_subscription, send_notification, get_sns_topic_arn

def send_test_message():
    """
    Send a test SMS message using the configured SNS topic
    """
    try:
        # Get SNS topic ARN
        sns_topic_arn = get_sns_topic_arn()
        
        if not sns_topic_arn:
            print("Error: SNS_TOPIC_ARN not found")
            return
            
        print(f"Using SNS Topic ARN: {sns_topic_arn}")
        
        # Subscribe phone number to topic
        phone_number = input("Enter phone number (e.g., +12345678900): ")
        print(f"\nSubscribing {phone_number} to SNS topic...")
        
        subscription_arn = manage_sns_subscription(phone_number, True)
        if subscription_arn:
            print(f"Subscription ARN: {subscription_arn}")
        else:
            print("Failed to subscribe phone number")
            return
        
        # Format test message
        message = "🎯 This is a test notification from Deadpool Game via SNS topic. If you received this, topic notifications are working!"
        
        # Send notification
        message_id = send_notification(message)
        
        if message_id:
            print("\nMessage sent successfully!")
            print(f"MessageId: {message_id}")
        else:
            print("Failed to send message")
        
    except ClientError as e:
        print(f"AWS Error: {e.response['Error']['Message']}")
        raise
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise

if __name__ == '__main__':
    send_test_message()