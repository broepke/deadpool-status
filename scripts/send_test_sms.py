#!/usr/bin/env python3
import boto3
import json
from botocore.exceptions import ClientError

def send_test_message():
    """
    Send a test SMS message using the configured SNS topic
    """
    try:
        # Get SNS topic ARN from Lambda environment
        lambda_client = boto3.client('lambda')
        response = lambda_client.get_function_configuration(
            FunctionName='deadpool-status-DeadpoolStatusChecker-7TIXErAlT44O'
        )
        sns_topic_arn = response['Environment']['Variables'].get('SNS_TOPIC_ARN')
        
        if not sns_topic_arn:
            print("Error: SNS_TOPIC_ARN not found in Lambda environment")
            return
            
        print(f"Using SNS Topic ARN: {sns_topic_arn}")
        
        # Initialize SNS client
        sns = boto3.client('sns')
        
        # Subscribe phone number to topic
        phone_number = '+1XXXXXXXXXX'
        print(f"\nSubscribing {phone_number} to SNS topic...")
        
        subscription = sns.subscribe(
            TopicArn=sns_topic_arn,
            Protocol='sms',
            Endpoint=phone_number
        )
        print(f"Subscription ARN: {subscription['SubscriptionArn']}")
        
        # Format test message
        message = "🎯 This is a test notification from Deadpool Game via SNS topic. If you received this, topic notifications are working!"
        
        # Publish to SNS topic
        response = sns.publish(
            TopicArn=sns_topic_arn,
            Message=message,
            MessageAttributes={
                'AWS.SNS.SMS.SMSType': {
                    'DataType': 'String',
                    'StringValue': 'Transactional'
                }
            }
        )
        
        print("\nMessage sent successfully!")
        print(f"MessageId: {response['MessageId']}")
        
    except ClientError as e:
        print(f"AWS Error: {e.response['Error']['Message']}")
        raise
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise

if __name__ == '__main__':
    send_test_message()