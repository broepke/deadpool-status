import boto3

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Deadpool')

# Test records
test_records = [
    {
        'PK': 'PERSON#9a2b9632-387f-4ead-a88d-dca42a6f746c',
        'SK': 'DETAILS',
        'Name': 'Richard Simmons',
        'WikiPage': 'Richard_Simmons'
    },
    {
        'PK': 'PERSON#ca6b88d2-ca64-4f46-a3f7-5e7d6d04fecc',
        'SK': 'DETAILS',
        'Name': 'Forest Whitaker',
        'WikiPage': 'Forest_Whitaker'
    }
]

# Update records
for record in test_records:
    print(f"Updating {record['Name']}...")
    table.put_item(Item=record)
    print(f"Updated {record['Name']}")

print("Test records updated successfully")