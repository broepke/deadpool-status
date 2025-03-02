# SMS Notification Issue Fix

## Issue Description

On March 1, 2025, the system failed to send SMS notifications to users when a death notification was supposed to be sent out. After investigation, we identified that the issue was caused by hidden Unicode characters in phone numbers stored in the DynamoDB database.

## Root Cause

1. Many phone numbers in the DynamoDB table contained invisible Unicode characters (like Right-To-Left Mark ‬ or Left-To-Right Mark ‭)
2. AWS SNS rejected these phone numbers as invalid endpoints with the error: "Invalid SMS endpoint"
3. As a result, only 2 out of 11 users who should receive notifications were actually subscribed to the SNS topic

## Solution

1. Created a `clean_phone_number` function in `src/utils/sns.py` that removes all non-standard characters from phone numbers
2. Modified the `manage_sns_subscription` and `send_verification_code` functions to use this cleaning function
3. Created a one-time fix script (`scripts/fix_phone_numbers.py`) to clean existing phone numbers in the database
4. Ran the `check_sns_subscriptions.py` script to subscribe all users to the SNS topic

## Verification

After applying the fix:
- All 11 users with SMS notifications enabled are now properly subscribed to the SNS topic
- The system will automatically clean any new phone numbers before subscribing them to the SNS topic
- Future death notifications should be delivered to all subscribed users

## Prevention

To prevent similar issues in the future:
1. The `clean_phone_number` function will automatically clean any phone numbers before they are used with SNS
2. Consider adding validation when phone numbers are initially stored in the database
3. Run the `check_sns_subscriptions.py` script periodically to ensure all users are properly subscribed

## Related Files

- `src/utils/sns.py` - Added phone number cleaning functionality
- `scripts/fix_phone_numbers.py` - One-time fix script to clean existing phone numbers
- `scripts/check_sns_subscriptions.py` - Script to check and fix SNS subscriptions