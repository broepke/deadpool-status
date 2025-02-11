# SMS Notification System Testing Plan

## Prerequisites
- ✅ AWS 10DLC phone number approved and ready
- ✅ SNS Topic configured
- ✅ DynamoDB table set up
- ✅ Lambda function configured with proper environment variables

## Testing Steps

### 1. Configure User SMS Settings
```bash
# Update user record with phone number
python scripts/update_user_sms.py <your_phone_number>
```
Expected outcome:
- User record updated with:
  - SmsNotificationsEnabled = True
  - PhoneVerified = False
  - PhoneNumber set to provided number

### 2. Verify Phone Number
```bash
# Send and verify verification code
python scripts/verify_phone.py <your_phone_number>
```
Expected outcome:
- Receive verification code via SMS
- After entering correct code:
  - PhoneVerified updated to True
  - Success message displayed

### 3. Test Death Notification System
```bash
# Run death notification simulation
python scripts/test_death_notification.py
```
Expected outcome:
- Test person record created
- Death date updated
- List of notification-enabled users displayed
- SNS Topic ARN confirmed
- Sample message displayed
- Test person record cleaned up

### 4. Verify Production Setup
Check the following in AWS Console:
1. SNS Console:
   - Confirm 10DLC number status
   - Review message delivery metrics
   - Check spending dashboard

2. CloudWatch:
   - Check Lambda function logs
   - Review any error messages
   - Monitor SMS delivery status

3. DynamoDB:
   - Verify user record updates
   - Confirm phone verification status
   - Check notification preferences

## Success Criteria
1. ✓ Verification code received on phone
2. ✓ User record shows verified status
3. ✓ Test notification system runs without errors
4. ✓ CloudWatch shows successful Lambda execution
5. ✓ SNS metrics show successful message delivery

## Error Handling Verification
1. Invalid phone numbers
2. Incorrect verification codes
3. Missing SNS permissions
4. DynamoDB update failures

## Monitoring
Monitor these metrics during testing:
- SMS delivery success rate
- Lambda execution times
- DynamoDB operation latency
- Error rates and types
- Cost per notification

## Rollback Plan
If issues are encountered:
1. Disable SMS notifications in user record
2. Document error conditions
3. Check CloudWatch logs for specific error messages
4. Review SNS delivery status
5. Verify AWS IAM permissions

## Next Steps After Successful Testing
1. Monitor production usage
2. Set up CloudWatch alarms
3. Configure cost alerts
4. Document any issues found
5. Update runbooks with learned procedures

## Notes
- Keep test phone numbers in E.164 format (+1XXXXXXXXXX)
- Monitor AWS SNS spending during testing
- Document any error messages for troubleshooting
- Save CloudWatch logs for future reference