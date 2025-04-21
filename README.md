# Deadpool Status Lambda

AWS Lambda function to check and update person records with Wikipedia data.

## Overview
This service maintains person records in DynamoDB by fetching and updating birth dates, death dates, and ages from Wikipedia/Wikidata. It runs on a nightly schedule using EventBridge.

## Project Structure
```
.
├── docs/
│   └── architecture.md     # Detailed architecture documentation
├── src/
│   ├── lambda_function.py  # Main Lambda handler
│   └── utils/
│       ├── dynamo.py       # DynamoDB operations
│       └── wiki.py         # Wikipedia/Wikidata operations
├── tests/                  # Unit and integration tests
├── requirements.txt        # Python dependencies
└── template.yaml           # AWS SAM template
```

## Prerequisites
- AWS CLI configured with appropriate credentials
- Python 3.9+
- AWS SAM CLI for local testing and deployment
- DynamoDB table with required schema (see architecture.md)

## Development Setup
1. Create Python virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Unix
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure local environment:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

## Local Testing
1. Test Lambda locally:
   ```bash
   sam local invoke -e events/schedule.json
   ```

## Deployment
1. Build SAM application:
   ```bash
   sam build
   ```

2. Deploy to AWS:
   ```bash
   sam deploy --guided
   ```

## Configuration
- `BATCH_SIZE`: Number of records to process in each batch (default: 25)
- `TABLE_NAME`: DynamoDB table name
- `LOG_LEVEL`: Logging level (default: INFO)

## Scheduling
The Lambda function is scheduled using Amazon EventBridge (CloudWatch Events). The schedule configuration is defined in `template.yaml`:

### Default Schedule
- Runs daily at 6:00 PM UTC (1:00 PM Central Time): `cron(0 18 * * ? *)`
- Automatic retries: Maximum 2 retry attempts on failure
- Timeout: 600 seconds (10 minutes)

### Modifying the Schedule
To change the schedule:

1. Edit the cron expression in `template.yaml`:
```yaml
Events:
  DailyCheck:
    Type: Schedule
    Properties:
      Schedule: cron(0 18 * * ? *)  # Modify this expression
```

Common cron patterns:
- Daily at midnight: `cron(0 0 * * ? *)`
- Every 6 hours: `cron(0 */6 * * ? *)`
- Every hour: `cron(0 * * * ? *)`
- Every 5 minutes: `cron(0/5 * * * ? *)`

2. Adjust retry policy if needed:
```yaml
RetryPolicy:
  MaximumRetryAttempts: 2  # Modify retry attempts
```

3. Deploy changes:
```bash
sam deploy
```

### Manual Triggers
You can also trigger the function manually through:
- AWS Console
- AWS CLI:
  ```bash
  aws lambda invoke --function-name deadpool-status-checker output.json
  ```

## Monitoring

### CloudWatch Logs
The Lambda function logs to the `/aws/lambda/deadpool-status-checker` log group. Below are useful CloudWatch Logs Insights queries for monitoring different aspects of the service:

1. Death Discoveries (New Deaths):
```
fields @timestamp, @message
| filter @message like "Found death date"
| parse @message "Found death date * for *" as death_date, person_name
| sort @timestamp desc
```

2. Failed Wiki Lookups:
```
fields @timestamp, @message
| filter @message like "No Wiki ID available"
| parse @message "No Wiki ID available for * (WikiPage: *)" as person_name, wiki_page
| sort @timestamp desc
```

3. Non-Death Updates (Age Changes):
```
fields @timestamp, @message
| filter @message like "Updated age"
| parse @message "Updated age from * to * for *" as old_age, new_age, person_name
| sort @timestamp desc
```

4. Processing Errors:
```
fields @timestamp, @message
| filter level = "ERROR"
| sort @timestamp desc
```

5. Execution Statistics:
```
fields @timestamp, @message
| filter @message like "Execution complete"
| parse @message "Execution complete - Duration: *s, Processed: *, Updated: *, Failed: *" as duration, processed, updated, failed
| sort @timestamp desc
```

### CloudWatch Metrics
- Custom metrics for tracking processing
- CloudWatch Alarms: Configured for error rates and duration

### Recent Updates
- Added comprehensive logging for person updates including death dates, age changes, and wiki lookup failures
- Implemented retry logic for API calls with exponential backoff
- Added detailed execution statistics logging
- Enhanced error handling and reporting

## Manual Trigger

Use the following command to trigger a single run (processes up to MAX_ITEMS_PER_RUN records):

```bash
aws lambda invoke --function-name deadpool-status-DeadpoolStatusChecker-7TIXErAlT44O --payload '{}' response.json
```

## Processing All Records

The Lambda function now supports pagination to process all records over multiple invocations. Each invocation processes a limited number of records (defined by MAX_ITEMS_PER_RUN environment variable) to avoid timeouts.

### Using the process_all_records.py Script

A helper script is provided to automatically process all records by repeatedly invoking the Lambda function:

```bash
# Make the script executable
chmod +x process_all_records.py

# Run the script with your Lambda function name
./process_all_records.py --function-name deadpool-status-DeadpoolStatusChecker-7TIXErAlT44O

# Optional parameters
./process_all_records.py --function-name deadpool-status-DeadpoolStatusChecker-7TIXErAlT44O --delay 10 --max-invocations 5
```

Parameters:
- `--function-name`: (Required) The name of your Lambda function
- `--delay`: (Optional) Delay between Lambda invocations in seconds (default: 5)
- `--max-invocations`: (Optional) Maximum number of Lambda invocations (0 for unlimited, default: 0)

### Manual Pagination

You can also manually paginate through records:

1. First invocation:
   ```bash
   aws lambda invoke --function-name deadpool-status-DeadpoolStatusChecker-7TIXErAlT44O --payload '{}' response.json
   ```

2. Check if there are more records:
   ```bash
   cat response.json | jq .body | jq -r | jq .hasMoreRecords
   ```

3. If true, get the pagination token:
   ```bash
   cat response.json | jq .body | jq -r | jq .paginationToken
   ```

4. Use the token for the next invocation:
   ```bash
   aws lambda invoke --function-name deadpool-status-DeadpoolStatusChecker-7TIXErAlT44O --payload '{"paginationToken": YOUR_TOKEN_HERE}' response.json
   ```

5. Repeat steps 2-4 until hasMoreRecords is false