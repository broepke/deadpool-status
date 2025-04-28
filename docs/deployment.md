# Deadpool Status Lambda: Build and Deployment Guide

This document provides comprehensive instructions for building, testing, and deploying the Deadpool Status Lambda function.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Development Environment Setup](#development-environment-setup)
3. [Local Testing](#local-testing)
4. [Building the SAM Application](#building-the-sam-application)
5. [Deployment Options](#deployment-options)
6. [Processing All Records](#processing-all-records)
7. [Monitoring and Troubleshooting](#monitoring-and-troubleshooting)
8. [Manual Operations](#manual-operations)
9. [Important Considerations](#important-considerations)

## Prerequisites

Before you begin, ensure you have the following:

- AWS CLI configured with appropriate credentials
- Python 3.9+
- AWS SAM CLI installed
- DynamoDB table with required schema (see [architecture.md](architecture.md))
- S3 bucket for deployment artifacts (default: "deadpool-status")

## Development Environment Setup

Follow these steps to set up your local development environment:

```bash
# Create a Python virtual environment
python -m venv venv

# Activate the virtual environment
source venv/bin/activate  # For Unix/Mac
# or
.\venv\Scripts\activate  # For Windows

# Install dependencies
pip install -r requirements.txt
```

### Installing AWS SAM CLI

If you don't have the AWS SAM CLI installed:

**For macOS:**
```bash
brew tap aws/tap
brew install aws-sam-cli
```

**For other platforms:**
Visit the [AWS SAM CLI installation guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html).

## Local Testing

Before deploying to AWS, test the function locally:

```bash
# Make sure you're in the project root directory
python run_local.py
```

This script:
1. Sets up necessary environment variables
2. Loads a test event from `events/schedule.json`
3. Invokes the Lambda handler function locally
4. Displays the execution results

The `run_local.py` script is configured to:
- Use a batch size of 10 records
- Process a maximum of 50 records per run
- Use "Deadpool" as the DynamoDB table name

You can modify these settings in the script if needed.

## Building the SAM Application

Build the SAM application to package your code and dependencies:

```bash
# Build the SAM application
sam build
```

This command:
1. Creates a `.aws-sam` directory
2. Installs dependencies from `requirements.txt`
3. Packages your application code
4. Prepares the deployment package

## Deployment Options

### Option 1: Guided Deployment (Recommended for First Deployment)

For first-time deployment or when you need to change configuration:

```bash
# Deploy with guided prompts
sam deploy --guided
```

This interactive process will prompt you for:
- Stack name (default: "deadpool-status")
- AWS Region (default: "us-east-1" from samconfig.toml)
- Parameter values (Environment: dev or prod)
- Confirmation of IAM role creation
- Deployment confirmation

Your responses will be saved to `samconfig.toml` for future deployments.

### Option 2: Using Existing Configuration

For subsequent deployments using the saved configuration:

```bash
# Deploy using existing configuration
sam deploy
```

This uses the settings in your `samconfig.toml` file:
- Stack name: "deadpool-status"
- S3 bucket: "deadpool-status"
- Region: "us-east-1"
- Capabilities: "CAPABILITY_IAM"

## Processing All Records

There are two ways to process all records:

### Option 1: Auto-Pagination (Recommended)

The Lambda function now includes an auto-pagination feature that allows it to process all records automatically without external orchestration:

1. Enable auto-pagination by setting these environment variables in template.yaml:
   ```yaml
   Environment:
     Variables:
       AUTO_PAGINATE: true
       MAX_AUTO_INVOCATIONS: 20
   ```

2. Deploy the updated template:
   ```bash
   sam deploy
   ```

3. Invoke the Lambda function once to start the process:
   ```bash
   aws lambda invoke --function-name deadpool-status-DeadpoolStatusChecker-XXXXXXXXXXXX --payload '{}' response.json
   ```

The Lambda function will automatically invoke itself to process subsequent batches until all records are processed or the maximum number of invocations is reached.

### Option 2: Using the process_all_records.py Script

If you prefer not to use auto-pagination, you can use the provided script:

```bash
# Get your Lambda function name from the deployment output
# It will be something like: deadpool-status-DeadpoolStatusChecker-XXXXXXXXXXXX

# Make the script executable
chmod +x process_all_records.py

# Run the script with your Lambda function name
./process_all_records.py --function-name deadpool-status-DeadpoolStatusChecker-XXXXXXXXXXXX
```

#### Optional Parameters

The script supports additional parameters:
```bash
# Set delay between invocations (default: 5 seconds)
--delay 10

# Limit the number of invocations (default: 0 for unlimited)
--max-invocations 5

# Example with all parameters
./process_all_records.py --function-name deadpool-status-DeadpoolStatusChecker-XXXXXXXXXXXX --delay 10 --max-invocations 5
```

## Monitoring and Troubleshooting

### CloudWatch Logs

View logs for the Lambda function:

```bash
# Using SAM CLI
sam logs -n DeadpoolStatusChecker --stack-name deadpool-status --tail

# Or using AWS CLI
aws logs get-log-events --log-group-name /aws/lambda/deadpool-status-DeadpoolStatusChecker-XXXXXXXXXXXX
```

### CloudWatch Logs Insights Queries

The following queries can be used in CloudWatch Logs Insights to monitor different aspects of the service:

#### 1. Death Discoveries (New Deaths)
```
fields @timestamp, @message
| filter @message like "Found death date"
| parse @message "Found death date * for *" as death_date, person_name
| sort @timestamp desc
```

#### 2. Failed Wiki Lookups
```
fields @timestamp, @message
| filter @message like "No Wiki ID available"
| parse @message "No Wiki ID available for * (WikiPage: *)" as person_name, wiki_page
| sort @timestamp desc
```

#### 3. Non-Death Updates (Age Changes)
```
fields @timestamp, @message
| filter @message like "Updated age"
| parse @message "Updated age from * to * for *" as old_age, new_age, person_name
| sort @timestamp desc
```

#### 4. Processing Errors
```
fields @timestamp, @message
| filter level = "ERROR"
| sort @timestamp desc
```

#### 5. Execution Statistics
```
fields @timestamp, @message
| filter @message like "Execution complete"
| parse @message "Execution complete - Duration: *s, Processed: *, Updated: *, Failed: *" as duration, processed, updated, failed
| sort @timestamp desc
```

## Manual Operations

### Manual Lambda Invocation

To manually trigger the Lambda function:

```bash
# Basic invocation
aws lambda invoke --function-name deadpool-status-DeadpoolStatusChecker-XXXXXXXXXXXX --payload '{}' response.json

# Check the response
cat response.json
```

### Manual Pagination

For manual pagination through records:

1. First invocation:
   ```bash
   aws lambda invoke --function-name deadpool-status-DeadpoolStatusChecker-XXXXXXXXXXXX --payload '{}' response.json
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
   aws lambda invoke --function-name deadpool-status-DeadpoolStatusChecker-XXXXXXXXXXXX --payload '{"paginationToken": "YOUR_TOKEN_HERE"}' response.json
   ```

5. Repeat steps 2-4 until hasMoreRecords is false

## Important Considerations

### 1. DynamoDB Table

The template assumes a DynamoDB table named "Deadpool" already exists. If it doesn't, you'll need to create it with the schema described in [architecture.md](architecture.md):

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

### 2. AWS Credentials

Ensure your AWS CLI is configured with appropriate credentials that have permissions to:
- Create and manage Lambda functions
- Create and manage IAM roles
- Create and manage CloudWatch Events
- Read/write to DynamoDB
- Use CloudWatch Logs

### 3. S3 Bucket

The deployment uses an S3 bucket named "deadpool-status" for storing deployment artifacts. Make sure this bucket exists in your account or update the `samconfig.toml` file.

### 4. Auto-Pagination Considerations

When using the auto-pagination feature:

- **Lambda Concurrency**: Each self-invocation runs as a separate Lambda invocation, which counts against your account's concurrency limits.
- **Billing**: Each self-invocation is billed separately as a new Lambda invocation.
- **Monitoring**: You can monitor the progress by checking CloudWatch Logs for each invocation.
- **Timeout**: If a single invocation times out, the auto-pagination chain will be broken. Ensure your Lambda timeout is sufficient for processing the batch size you've configured.
- **Error Handling**: If an error occurs during processing, the auto-pagination chain will be broken. Check CloudWatch Logs for error messages.
- **IAM Permissions**: The Lambda function needs permission to invoke itself. This is configured in the template.yaml file using a resource pattern that avoids circular dependencies.

### 5. Rate Limiting

The code includes retry logic and rate limiting protection for Wikipedia/Wikidata API calls, but be aware that processing large numbers of records might still hit API limits. Consider:
- Using the `--delay` parameter with `process_all_records.py`
- Adjusting the `BATCH_SIZE` environment variable
- Implementing additional rate limiting if needed

### 6. SNS Notifications

For death notifications, ensure the SNS topic ARN is properly configured. You can set it via:
- Environment variable: `SNS_TOPIC_ARN`
- CloudFormation output from another stack

### 7. Scheduling

The Lambda function is scheduled to run daily at 6:00 PM UTC (1:00 PM Central Time) by default. To modify this:

1. Edit the cron expression in `template.yaml`:
```yaml
Events:
  DailyCheck:
    Type: Schedule
    Properties:
      Schedule: cron(0 18 * * ? *)  # Modify this expression
```

2. Deploy the changes:
```bash
sam deploy
```

Common cron patterns:
- Daily at midnight: `cron(0 0 * * ? *)`
- Every 6 hours: `cron(0 */6 * * ? *)`
- Every hour: `cron(0 * * * ? *)`
- Every 5 minutes: `cron(0/5 * * * ? *)`