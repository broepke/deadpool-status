# Death Notification System Architecture

## Overview
This document outlines the architecture for adding death notifications to the existing AWS Lambda Person Status Checker service. The system will notify players when a person's death is detected during the daily status check.

## Design Decision: SMS via SNS

### Why SMS over Email?
1. **Higher Engagement**: SMS has higher open rates and immediate visibility
2. **Game Context**: More suitable for time-sensitive game notifications
3. **Simple Integration**: AWS SNS provides straightforward SMS capabilities
4. **Cost Effective**: Pay-per-use pricing with AWS SNS

### Why AWS SNS?
1. **Native AWS Integration**: Seamless integration with existing Lambda and other AWS services
2. **Reliable Delivery**: Built-in retry mechanisms and delivery tracking
3. **Scalability**: Can handle high volume of notifications
4. **Multiple Channels**: Flexibility to add email or other notification types in future

## Component Architecture

### 1. Contact Information Storage
**Recommendation**: Store in DynamoDB (Same table, new entity type)

**Rationale**:
- Keeps user data consolidated in one place
- Reduces cross-service dependencies
- Simpler access patterns
- More flexible than Cognito for game-specific data

**Data Structure**:
```json
{
  "PK": "USER#uuid",
  "SK": "PROFILE",
  "PhoneNumber": "string",
  "NotificationPreferences": {
    "smsEnabled": boolean,
    "deathNotifications": boolean
  },
  "PhoneVerified": boolean,
  "LastNotified": "string (ISO-8601)"
}
```

### 2. Phone Number Verification
1. **Verification Flow**:
   - User submits phone number
   - Lambda triggers SNS verification
   - User receives verification code
   - Code validation updates DynamoDB PhoneVerified status

### 3. Enhanced Lambda Function
Add notification logic to existing Lambda:

1. **Death Detection**:
   ```python
   if old_record.get('DeathDate') is None and new_record.get('DeathDate') is not None:
       trigger_death_notification(person_name, death_date)
   ```

2. **Notification Handling**:
   - Batch notifications to reduce API calls
   - Include retry logic
   - Track notification status

### 4. SNS Topic Structure
```yaml
DeathNotificationTopic:
  Type: AWS::SNS::Topic
  Properties:
    DisplayName: "Deadpool Game"
    TopicName: "death-notifications"
```

### 5. Message Format
```json
{
  "default": "Person {name} has died on {date}",
  "sms": "🎯 {name} has passed away on {date}. Check the game for updates!"
}
```

## Data Flow

1. **Daily Check Process**:
   - Lambda detects death date changes
   - Identifies new deaths
   - Queries for users with notifications enabled
   - Batches notifications

2. **Notification Process**:
   - Lambda publishes to SNS topic
   - SNS handles SMS delivery
   - Status tracked in CloudWatch
   - Failed notifications logged for retry

## Security Considerations

1. **Phone Numbers**:
   - Encrypt at rest in DynamoDB
   - Mask in logs and UI
   - Implement rate limiting for verification

2. **SNS Configuration**:
   - Use account-level SMS settings
   - Monitor spending limits
   - Implement anti-spam measures

3. **Access Control**:
   - Strict IAM permissions for SNS
   - Audit logging for all notification attempts

## Infrastructure Updates

### 1. DynamoDB Updates
- Add GSI for user queries
- Update IAM permissions

### 2. New IAM Permissions
```yaml
- SNSPublishPolicy:
    TopicName: !Ref DeathNotificationTopic
- SNSSMSPolicy:
    Effect: Allow
    Action: 
      - sns:Publish
      - sns:CheckIfPhoneNumberIsOptedOut
      - sns:OptInPhoneNumber
```

### 3. Lambda Environment Variables
```yaml
SNS_TOPIC_ARN: !Ref DeathNotificationTopic
SMS_ENABLED: true
NOTIFICATION_BATCH_SIZE: 100
```

## Monitoring & Alerts

1. **CloudWatch Metrics**:
   - SMS delivery success rate
   - Notification latency
   - Failed notification count
   - Phone verification success rate

2. **Cost Monitoring**:
   - SNS usage metrics
   - SMS cost tracking
   - Set up billing alerts

## Cost Optimization

1. **Batch Processing**:
   - Group notifications
   - Implement rate limiting
   - Cache user preferences

2. **SMS Specific**:
   - Use short message format
   - Monitor opt-out rates
   - Implement quiet hours

## Future Enhancements

1. **Additional Channels**:
   - Email integration
   - Push notifications
   - Discord/Slack webhooks

2. **Advanced Features**:
   - Custom notification templates
   - User notification preferences
   - Notification history
   - Analytics dashboard

## Implementation Steps

1. **Phase 1: Core SMS**
   - Update DynamoDB schema
   - Implement phone verification
   - Set up SNS topic
   - Add notification logic to Lambda

2. **Phase 2: Management**
   - Add user preferences
   - Implement monitoring
   - Create admin dashboard

3. **Phase 3: Optimization**
   - Add batching
   - Implement caching
   - Optimize costs