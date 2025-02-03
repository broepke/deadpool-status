#!/usr/bin/env python3
import boto3
import os
import random
import time
from botocore.exceptions import ClientError

def generate_verification_code():
    """Generate a 6-digit verification code"""
    return str(random.randint(100000, 999999))

def send_verification_code(phone_number: str, code: str):
    """Send verification code via SNS"""
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
        return response['MessageId']
    except ClientError as e:
        print(f"Error sending verification code: {e.response['Error']['Message']}")
        raise

def verify_phone_number(phone_number: str):
    """Handle phone number verification process"""
    # Generate verification code
    code = generate_verification_code()
    
    try:
        # Send verification code
        message_id = send_verification_code(phone_number, code)
        print(f"Verification code sent. MessageId: {message_id}")
        
        # Get user input for verification
        user_input = input("Enter the verification code you received: ")
        
        if user_input.strip() == code:
            # Update DynamoDB record
            dynamodb = boto3.resource('dynamodb')
            table = dynamodb.Table('Deadpool')
            user_id = "34b83458-5041-7025-f53a-506e8e47578b"
            
            response = table.update_item(
                Key={
                    'PK': f'PLAYER#{user_id}',
                    'SK': 'DETAILS'
                },
                UpdateExpression='SET PhoneVerified = :verified',
                ExpressionAttributeValues={
                    ':verified': True
                },
                ReturnValues='ALL_NEW'
            )
            
            print("\nPhone number successfully verified!")
            print("Updated user record:")
            print(response['Attributes'])
            return True
        else:
            print("\nVerification failed: Code does not match")
            return False
            
    except ClientError as e:
        print(f"Error in verification process: {e.response['Error']['Message']}")
        raise
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print("Usage: python verify_phone.py <phone_number>")
        print("Example: python verify_phone.py +12345678900")
        sys.exit(1)
    
    phone_number = sys.argv[1]
    # Validate phone number format
    if not phone_number.startswith('+'):
        print("Error: Phone number must start with + and include country code")
        print("Example: +12345678900")
        sys.exit(1)
    
    verify_phone_number(phone_number)