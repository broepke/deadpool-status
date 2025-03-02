#!/usr/bin/env python3
import boto3
from botocore.exceptions import ClientError
import sys
import os

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from utils.sns import manage_sns_subscription

def clean_phone_number(phone):
    """Clean phone number by removing all non-standard characters"""
    # Keep only +, digits, and standard ASCII characters
    cleaned = ''
    for char in phone:
        if char == '+' or char.isdigit():
            cleaned += char
    return cleaned

def fix_phone_numbers():
    """Fix phone numbers in DynamoDB by removing hidden Unicode characters"""
    # Initialize DynamoDB client
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('Deadpool')
    
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
    
    # Set the SNS_TOPIC_ARN in the environment for the manage_sns_subscription function
    os.environ['SNS_TOPIC_ARN'] = sns_topic_arn
    
    try:
        # Get all users with SMS notifications enabled
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
        print(f"Found {len(users)} verified users with SMS notifications enabled")
        
        fixed_count = 0
        for user in users:
            user_id = user['PK'].replace('PLAYER#', '')
            name = f"{user.get('FirstName', '')} {user.get('LastName', '')}"
            phone = user.get('PhoneNumber', '')
            
            # Clean the phone number
            cleaned_phone = clean_phone_number(phone)
            
            print(f"\nChecking {name}")
            print(f"Original phone: {phone}")
            print(f"Cleaned phone: {cleaned_phone}")
            
            # Check if the phone number changed
            if phone != cleaned_phone:
                print(f"Fixing phone number for {name}")
                
                # Update the user record with the cleaned phone number
                response = table.update_item(
                    Key={
                        'PK': f'PLAYER#{user_id}',
                        'SK': 'DETAILS'
                    },
                    UpdateExpression='SET PhoneNumber = :phone',
                    ExpressionAttributeValues={
                        ':phone': cleaned_phone
                    },
                    ReturnValues='ALL_NEW'
                )
                
                print(f"Updated phone number in DynamoDB")
                fixed_count += 1
                
                # Try to subscribe the user with the cleaned phone number
                try:
                    subscription_arn = manage_sns_subscription(cleaned_phone, True)
                    if subscription_arn:
                        print(f"Successfully subscribed {cleaned_phone} to notifications")
                except Exception as e:
                    print(f"Error subscribing {cleaned_phone}: {str(e)}")
            else:
                print(f"Phone number is already clean")
        
        print(f"\nFixed {fixed_count} phone numbers")
        
    except ClientError as e:
        print(f"Error: {e.response['Error']['Message']}")
        raise
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise

if __name__ == '__main__':
    fix_phone_numbers()