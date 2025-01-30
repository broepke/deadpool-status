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
   python -m venv .venv
   source .venv/bin/activate  # Unix
   .venv\Scripts\activate     # Windows
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
1. Run unit tests:
   ```bash
   python -m pytest tests/
   ```

2. Test Lambda locally:
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

## Monitoring
- CloudWatch Logs: `/aws/lambda/deadpool-status-checker`
- CloudWatch Metrics: Custom metrics for tracking processing
- CloudWatch Alarms: Configured for error rates and duration

## Contributing
1. Fork the repository
2. Create feature branch
3. Commit changes
4. Create pull request

## License
MIT License
