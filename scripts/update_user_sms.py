#!/usr/bin/env python3
import boto3
import os
from botocore.exceptions import ClientError

def update_user_sms_preferences(phone_number: str):
    """Update specific user record with SMS notification fields and phone number"""
    
    # Initialize DynamoDB client
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('Deadpool')
    
    # User ID for Brian Roepke
    user_id = "34b83458-5041-7025-f53a-506e8e47578b"
    
    try:
        # Update the user record with new SMS fields
        response = table.update_item(
            Key={
                'PK': f'PLAYER#{user_id}',
                'SK': 'DETAILS'
            },
            UpdateExpression='SET SmsNotificationsEnabled = :sms, PhoneVerified = :verified, PhoneNumber = :phone',
            ExpressionAttributeValues={
                ':sms': True,  # Enable SMS notifications by default
                ':verified': False,  # Phone number needs to be verified
                ':phone': phone_number
            },
            ReturnValues='ALL_NEW'
        )
        
        print("Successfully updated user record:")
        print(response['Attributes'])
        
    except ClientError as e:
        print(f"Error updating user record: {e.response['Error']['Message']}")
        raise
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise

if __name__ == '__main__':
    # Get phone number from command line argument
    import sys
    if len(sys.argv) != 2:
        print("Usage: python update_user_sms.py <phone_number>")
        print("Example: python update_user_sms.py +12345678900")
        sys.exit(1)
    
    phone_number = sys.argv[1]
    # Validate phone number format (must start with + and country code)
    if not phone_number.startswith('+'):
        print("Error: Phone number must start with + and include country code")
        print("Example: +12345678900")
        sys.exit(1)
        
    update_user_sms_preferences(phone_number)