# AWS Lambda Person Status Checker Architecture

## Overview
This service checks and updates person records in DynamoDB with birth dates, death dates, and ages fetched from Wikipedia/Wikidata. It runs nightly via EventBridge scheduling.

## Components

### 1. AWS Lambda Function
- **Runtime**: Python 3.9+
- **Memory**: 256MB (adjustable based on performance needs)
- **Timeout**: 5 minutes (adjustable based on record volume)
- **Handler**: `lambda_function.lambda_handler`

### 2. DynamoDB Integration
- **Table Structure**:
  ```json
  {
    "PK": "PERSON#uuid",
    "SK": "DETAILS",
    "Name": "string",
    "BirthDate": "string (ISO-8601)",
    "DeathDate": "string (ISO-8601)",
    "Age": "number",
    "WikiID": "string",
    "WikiPage": "string"
  }
  ```
- **Queries**:
  - GSI on SK for efficient filtering of DETAILS records
  - Filter for missing DeathDate field

### 3. Wikipedia/Wikidata Integration
- Reuse existing Wiki utilities for:
  - Fetching Wiki IDs
  - Resolving redirects
  - Getting birth/death dates
- Implement caching using Lambda layer for `@lru_cache`
- Retry logic for API resilience

### 4. EventBridge Scheduling
- **Schedule**: Daily at midnight UTC
- **Rule Target**: Lambda function
- **Retry Policy**: 2 retries with exponential backoff

### 5. Error Handling & Monitoring
- CloudWatch Logs integration
- Custom metrics:
  - Records processed
  - Wiki API failures
  - DynamoDB operation latency
  - Records updated

## Data Flow

1. **Trigger**: EventBridge triggers Lambda function nightly
2. **Data Retrieval**: 
   - Query DynamoDB for records without death dates
   - Batch processing in groups of 25 records
3. **Wiki Processing**:
   - For each person:
     1. Get/verify WikiID
     2. Fetch birth/death dates
     3. Calculate age
4. **Data Update**:
   - Batch write updates back to DynamoDB
   - Only update changed records (compare hash)

## Security

- **IAM Roles**:
  - DynamoDB read/write permissions
  - CloudWatch Logs permissions
  - No VPC access required (public API calls only)

## Cost Optimization

1. **Lambda**:
   - Optimize memory allocation
   - Use batch processing
2. **DynamoDB**:
   - Use GSI for efficient queries
   - Implement batch writes
3. **API Calls**:
   - Implement caching
   - Batch process records

## Monitoring & Alerting

1. **CloudWatch Metrics**:
   - Function duration
   - Error rates
   - Records processed
2. **CloudWatch Alarms**:
   - Error rate threshold
   - Duration threshold
   - Failed record threshold

## Future Considerations

1. **Scaling**:
   - Implement parallel processing for large datasets
   - Consider Step Functions for complex orchestration
2. **Resilience**:
   - Dead letter queue for failed records
   - Circuit breaker for Wiki API
3. **Enhancement**:
   - Add additional Wiki data points
   - Implement change history tracking