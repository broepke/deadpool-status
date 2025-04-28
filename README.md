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
- Timeout: 900 seconds (15 minutes)

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

6. Error Counts by Date
```
# Extract all error and warning messages
filter level = "ERROR" or @message like "[ERROR]" or @message like "Error" or @message like "error" or @message like "exception" 
or level = "WARNING" or @message like "[WARNING]" or @message like "Warning" or @message like "warning"

# Parse out specific error types
| parse @message "Error * for *:" as error_type, entity_name
| parse @message "Error processing * for *: *" as operation, entity, error_details
| parse @message "Error in main processing loop: *" as main_error
| parse @message "Error getting * for *: *" as data_type, entity_id, api_error
| parse @message "Error scanning table: *" as dynamo_error
| parse @message "Error performing batch write: *" as batch_error
| parse @message "Error managing SNS subscription: *" as sns_error
| parse @message "Error sending notification: *" as notification_error
| parse @message "Rate limited. Retry-After: * seconds" as retry_after

# Group errors by type
| stats 
    count(*) as error_count,
    count_distinct(entity_name) as affected_entities,
    count(if(dynamo_error != '', 1, 0)) as dynamo_errors,
    count(if(@message like "Error scanning table%", 1, 0)) as scan_errors,
    count(if(@message like "Error performing batch write%", 1, 0)) as batch_write_errors,
    count(if(@message like "All retries failed for Wikidata fetch", 1, 0)) as wikidata_failures,
    count(if(@message like "Rate limited%", 1, 0)) as rate_limit_hits,
    count(if(@message like "Error sending notification%", 1, 0)) as notification_errors,
    count(if(@message like "SNS topic ARN not found", 1, 0)) as sns_config_errors,
    count(if(@message like "Error in main processing loop%", 1, 0)) as main_loop_errors
    by bin(30m) as time_window

# Sort by time window to see error patterns
| sort time_window desc

# Display detailed error messages for investigation
| fields @timestamp, @message, @error_type, @entity_name, @operation, @entity, @error_details, 
         @main_error, @data_type, @entity_id, @api_error, @dynamo_error, @batch_error, 
         @sns_error, @notification_error, @retry_after
```

7. Error Specifics
```
# Get all errors from the past 7 days
filter level = "ERROR" or @message like "[ERROR]" or @message like "Error"
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

### Auto-Pagination Feature

The Lambda function now includes an auto-pagination feature that allows it to process all records automatically without external orchestration. When enabled, the Lambda function will invoke itself asynchronously to process the next batch of records when it finishes processing the current batch.

To enable auto-pagination:

1. Set the `AUTO_PAGINATE` environment variable to `true` in the template.yaml file or in the Lambda console.
2. Set the `MAX_AUTO_INVOCATIONS` environment variable to limit the number of self-invocations (default: 20).

This feature is useful for processing large datasets without requiring Step Functions or external orchestration. The Lambda function will continue to invoke itself until either:
- All records are processed
- The maximum number of invocations is reached
- An error occurs

Each invocation will log its progress and include running totals in the response.

**Note:** Be mindful of AWS Lambda concurrency limits and costs when using this feature. Each self-invocation counts as a separate Lambda invocation for billing purposes.

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