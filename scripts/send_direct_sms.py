#!/usr/bin/env python3
import boto3
from botocore.exceptions import ClientError

def send_direct_sms():
    """
    Send a test SMS message directly using SNS (not through a topic)
    """
    try:
        # Initialize SNS client
        sns = boto3.client('sns')
        
        # Phone number to send to
        phone_number = '+1XXXXXXXXXX'
        
        # Format test message
        message = "🎯 This is a direct test SMS from Deadpool Game. If you received this, direct SMS is working!"
        
        print(f"Sending direct SMS to {phone_number}")
        
        # Send SMS directly
        response = sns.publish(
            PhoneNumber=phone_number,
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
    send_direct_sms()