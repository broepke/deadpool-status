# Phone Number Verification Guide

## Overview
To receive death notifications via SMS, users need to:
1. Add their phone number
2. Verify the number through a verification code process

## Verification Process

### Step 1: Add Phone Number
Users can add their phone number using the update_user_sms.py script:
```bash
python scripts/update_user_sms.py +1XXXXXXXXXX
```
- Phone number must be in E.164 format (e.g., +14155479222)
- This sets SmsNotificationsEnabled to True
- Sets PhoneVerified to False initially

### Step 2: Verify Phone Number
Users verify their phone number using verify_phone.py:
```bash
python scripts/verify_phone.py +1XXXXXXXXXX
```
The process:
1. System sends a 6-digit verification code via SMS
2. User receives the code on their phone
3. User enters the code when prompted
4. Upon successful verification:
   - PhoneVerified is set to True
   - User can now receive death notifications

## Example Flow
```bash
# 1. Add phone number
python scripts/update_user_sms.py +14155479222

# 2. Verify the number
python scripts/verify_phone.py +14155479222

# 3. Enter verification code when prompted
> Enter the verification code you received: 123456
```

## Important Notes
- Phone numbers must include country code
- Verification codes expire after a short period
- Users can re-run verification if the code expires
- Failed verifications don't affect existing settings
- Users can update their number at any time using the same process

## Troubleshooting
If verification fails:
1. Check phone number format
2. Ensure phone can receive SMS
3. Try requesting a new code
4. Contact support if issues persist