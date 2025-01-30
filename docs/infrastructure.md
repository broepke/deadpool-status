# Infrastructure Requirements

## AWS SAM Template Structure

The following resources will need to be defined in the SAM template:

### Lambda Function
```yaml
DeadpoolStatusChecker:
  Type: AWS::Serverless::Function
  Properties:
    Handler: lambda_function.lambda_handler
    Runtime: python3.9
    MemorySize: 256
    Timeout: 300
    Environment:
      Variables:
        TABLE_NAME: !Ref PersonTable
        BATCH_SIZE: 25
        LOG_LEVEL: INFO
    Events:
      DailyCheck:
        Type: Schedule
        Properties:
          Schedule: cron(0 0 * * ? *)
          RetryPolicy:
            MaximumRetryAttempts: 2
```

### DynamoDB Table
```yaml
PersonTable:
  Type: AWS::DynamoDB::Table
  Properties:
    BillingMode: PAY_PER_REQUEST
    AttributeDefinitions:
      - AttributeName: PK
        AttributeType: S
      - AttributeName: SK
        AttributeType: S
    KeySchema:
      - AttributeName: PK
        KeyType: HASH
      - AttributeName: SK
        KeyType: RANGE
    GlobalSecondaryIndexes:
      - IndexName: SK-PK-index
        KeySchema:
          - AttributeName: SK
            KeyType: HASH
          - AttributeName: PK
            KeyType: RANGE
        Projection:
          ProjectionType: ALL
```

### IAM Role Permissions
The Lambda function will need these permissions:
```yaml
Policies:
  - DynamoDBCrudPolicy:
      TableName: !Ref PersonTable
  - CloudWatchPutMetricPolicy: {}
  - Statement:
      - Effect: Allow
        Action:
          - logs:CreateLogGroup
          - logs:CreateLogStream
          - logs:PutLogEvents
        Resource: '*'
```

## Required Python Dependencies
```
boto3>=1.26.0
requests>=2.28.0
python-dateutil>=2.8.2
```

## Local Development Setup
1. AWS SAM CLI
2. Python 3.9+
3. AWS credentials configured
4. DynamoDB local for testing (optional)

## Deployment Considerations
1. **Regions**: Deploy to region closest to DynamoDB table
2. **Monitoring**:
   - CloudWatch Log groups
   - Custom metrics namespace
   - Alarms for error rates
3. **Cost Optimization**:
   - Optimize Lambda memory
   - Use DynamoDB auto-scaling
   - Implement efficient batch processing

## Security Requirements
1. **IAM**:
   - Least privilege access
   - Resource-based policies
2. **Data**:
   - Enable DynamoDB encryption at rest
   - Use AWS KMS for key management
3. **Monitoring**:
   - Enable CloudTrail
   - Configure CloudWatch Logs retention

## Next Steps
1. Switch to Code mode to implement:
   - SAM template
   - Lambda function
   - Utility modules
2. Create CI/CD pipeline
3. Set up monitoring and alerting
4. Implement testing strategy