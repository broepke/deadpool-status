# AWS SNS SMS Setup Guide

## Initial Setup Steps

1. First: Register for 10DLC
   - Go to the Amazon SNS console
   - In left navigation, choose "Text messaging (SMS)"
   - Under "Mobile text messaging (SMS)" select "10DLC campaigns"
   - Click "Register company"
   - Fill out company registration form
   - After company is registered, create a 10DLC campaign
     * Campaign type: Transactional
     * Use case: Account notifications
     * Sample message: "🎯 [Person Name] has passed away on [Date]. Check the game for updates!"
     * Monthly volume: Low (< 3000)

2. After 10DLC Registration:
   - Wait for company and campaign verification (usually a few hours)
   - Request a phone number for your campaign
   - This becomes your origination number

3. Then Add Sandbox Destination:
   - Go to "Text messaging (SMS)" in SNS console
   - Under "Sandbox destination phone numbers"
   - Click "Add phone number"
   - Enter your phone number (+14155479222)
   - Follow verification process

## Moving to Production

1. Request Production Access:
   - Go to the Amazon SNS console
   - In the left navigation pane, choose "Text messaging (SMS)"
   - Look for the "Sandbox status" section
   - Click "Request production access"
   - Fill out the form with:
     * Monthly SMS spend limit (suggest starting with $100)
     * Use case (Transactional)
     * Company name and description
     * Additional details about your SMS use case

2. Set up SMS Preferences:
   - Set monthly spending limit
   - Choose "Transactional" as default message type
   - Enable usage reports
   - Set default sender ID (optional)

## Additional Settings

1. Set up CloudWatch alarms for SMS spending
2. Configure delivery status logging
3. Set up monthly budget alerts

## Important Notes

- 10DLC registration is required for US numbers
- Production access approval typically takes 24-48 hours
- Keep your monthly spending limit reasonable
- Monitor SMS costs regularly

## Troubleshooting

Common issues:
- No origination entities (Need 10DLC registration)
- Sandbox restrictions
- Spending limit reached
- Phone number format issues
- Carrier filtering

If you encounter issues:
1. Check CloudWatch logs
2. Verify phone number format
3. Confirm spending limits
4. Check account status in SNS console
5. Verify 10DLC registration status