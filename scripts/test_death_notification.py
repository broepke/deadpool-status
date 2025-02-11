#!/usr/bin/env python3
import boto3
import json
from datetime import datetime
from botocore.exceptions import ClientError

def test_death_notification():
    """
    Test the death notification system by creating a test death record
    and sending actual SMS notifications
    """
    # Initialize DynamoDB client
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('Deadpool')
    
    # Create a test person record
    test_person_id = "TEST_PERSON_001"
    test_person = {
        'PK': f'PERSON#{test_person_id}',
        'SK': 'DETAILS',
        'Name': 'Test Person',
        'BirthDate': '1930-01-01',
        'WikiID': 'Q12345'
    }
    
    try:
        # First, create/update the test person without death date
        table.put_item(Item=test_person)
        print("Created test person record:")
        print(json.dumps(test_person, indent=2))
        
        # Now simulate finding their death
        test_person['DeathDate'] = datetime.now().strftime('%Y-%m-%d')
        table.put_item(Item=test_person)
        print("\nUpdated test person with death date:")
        print(json.dumps(test_person, indent=2))
        
        # Get notification-enabled users using scan instead of query
        response = table.scan(
            FilterExpression='begins_with(PK, :prefix) AND SK = :sk AND attribute_exists(SmsNotificationsEnabled)',
            ExpressionAttributeValues={
                ':prefix': 'PLAYER#',
                ':sk': 'DETAILS'
            }
        )
        
        users = response.get('Items', [])
        print(f"\nFound {len(users)} users with notification settings:")
        for user in users:
            print(f"- {user.get('FirstName')} {user.get('LastName')}")
            print(f"  Phone: {user.get('PhoneNumber')}")
            print(f"  SMS Enabled: {user.get('SmsNotificationsEnabled')}")
            print(f"  Verified: {user.get('PhoneVerified')}")
        
        # Get SNS topic ARN from Lambda environment
        lambda_client = boto3.client('lambda')
        response = lambda_client.get_function_configuration(
            FunctionName='deadpool-status-DeadpoolStatusChecker-7TIXErAlT44O'
        )
        sns_topic_arn = response['Environment']['Variables'].get('SNS_TOPIC_ARN')
        
        print(f"\nSNS Topic ARN: {sns_topic_arn}")
        
        # Format and send the actual message
        message = f"🎯 {test_person['Name']} has passed away on {test_person['DeathDate']}. Check the game for updates!"
        print("\nSending message:")
        print(message)
        
        # Initialize SNS client and send message
        sns = boto3.client('sns')
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
        
        print(f"\nNotification sent successfully!")
        print(f"MessageId: {response['MessageId']}")
        
        print("\nTest completed successfully!")
        
    except ClientError as e:
        print(f"Error during test: {e.response['Error']['Message']}")
        raise
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise
    finally:
        # Clean up test person record
        try:
            table.delete_item(
                Key={
                    'PK': f'PERSON#{test_person_id}',
                    'SK': 'DETAILS'
                }
            )
            print("\nCleaned up test person record")
        except Exception as e:
            print(f"Error cleaning up test record: {str(e)}")

if __name__ == '__main__':
    test_death_notification()