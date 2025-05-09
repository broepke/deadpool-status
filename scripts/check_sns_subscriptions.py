#!/usr/bin/env python3
import sys
import os
import boto3
from botocore.exceptions import ClientError

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from utils.sns import manage_sns_subscription, get_sns_topic_arn

def check_and_fix_subscriptions():
    """
    Check SNS topic subscriptions and add missing phone numbers
    """
    try:
        # Get SNS topic ARN
        sns_topic_arn = get_sns_topic_arn()
        if not sns_topic_arn:
            print("Error: SNS_TOPIC_ARN not found")
            return
            
        print(f"Using SNS Topic ARN: {sns_topic_arn}")
        
        # Initialize SNS client
        sns = boto3.client('sns')
        
        # Get current subscriptions
        subscriptions = sns.list_subscriptions_by_topic(TopicArn=sns_topic_arn)
        print("\nCurrent subscriptions:")
        for sub in subscriptions.get('Subscriptions', []):
            print(f"- Endpoint: {sub.get('Endpoint')}")
            print(f"  Protocol: {sub.get('Protocol')}")
            print(f"  Status: {sub.get('SubscriptionArn')}")
        
        # Get users from DynamoDB
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('Deadpool')
        
        response = table.scan(
            FilterExpression='begins_with(PK, :prefix) AND SK = :sk AND SmsNotificationsEnabled = :enabled AND PhoneVerified = :verified',
            ExpressionAttributeValues={
                ':prefix': 'PLAYER#',
                ':sk': 'DETAILS',
                ':enabled': True,
                ':verified': True
            }
        )
        
        users = response.get('Items', [])
        print(f"\nFound {len(users)} verified users:")
        
        # Check and add subscriptions for each verified user
        current_endpoints = [sub.get('Endpoint') for sub in subscriptions.get('Subscriptions', [])]
        
        for user in users:
            phone = user.get('PhoneNumber')
            name = f"{user.get('FirstName', '')} {user.get('LastName', '')}"
            print(f"\nChecking {name} ({phone})")
            
            if phone not in current_endpoints:
                print(f"Adding subscription for {phone}")
                subscription_arn = manage_sns_subscription(phone, True)
                if subscription_arn:
                    print(f"Subscription created: {subscription_arn}")
                else:
                    print(f"Failed to subscribe {phone}")
            else:
                print("Already subscribed")
        
        print("\nSubscription check complete!")
        
    except ClientError as e:
        print(f"AWS Error: {e.response['Error']['Message']}")
        raise
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise

if __name__ == '__main__':
    check_and_fix_subscriptions()