#!/usr/bin/env python3
"""
Script to remove the DisplayName attribute from the SNS topic
"""

import boto3
import os
import sys
import logging
from botocore.exceptions import ClientError

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_sns_topic_arn():
    """Get the SNS topic ARN from environment variables or CloudFormation outputs"""
    # Try to get from environment variable first
    sns_topic_arn = os.environ.get('SNS_TOPIC_ARN')
    if sns_topic_arn:
        return sns_topic_arn
    
    # If not available, try to get from CloudFormation outputs
    try:
        cloudformation = boto3.client('cloudformation')
        response = cloudformation.describe_stacks(StackName='deadpool-status')
        
        for stack in response['Stacks']:
            for output in stack.get('Outputs', []):
                if output.get('OutputKey') == 'NotificationTopicArn':
                    return output.get('OutputValue')
    except ClientError as e:
        logger.error(f"Error getting stack outputs: {e}")
    
    return None

def update_display_name(topic_arn, new_display_name="DP"):
    """Update the DisplayName attribute of the SNS topic to a minimal value"""
    if not topic_arn:
        logger.error("No SNS topic ARN provided")
        return False
    
    try:
        sns = boto3.client('sns')
        
        # Get current attributes
        response = sns.get_topic_attributes(TopicArn=topic_arn)
        attributes = response.get('Attributes', {})
        
        # Check if DisplayName exists
        if 'DisplayName' in attributes:
            logger.info(f"Current DisplayName: {attributes['DisplayName']}")
            
            # Set DisplayName to a minimal value (AWS requires a non-empty DisplayName for SMS)
            sns.set_topic_attributes(
                TopicArn=topic_arn,
                AttributeName='DisplayName',
                AttributeValue=new_display_name
            )
            
            logger.info(f"Successfully updated DisplayName to '{new_display_name}'")
            return True
        else:
            logger.info("No DisplayName attribute found on the SNS topic")
            return True
    
    except ClientError as e:
        logger.error(f"Error updating SNS topic: {e}")
        return False

def main():
    """Main function"""
    topic_arn = get_sns_topic_arn()
    
    if not topic_arn:
        logger.error("Could not determine SNS topic ARN")
        sys.exit(1)
    
    logger.info(f"Found SNS topic ARN: {topic_arn}")
    
    # Use a minimal display name (will appear as "DP> " in SMS messages)
    if update_display_name(topic_arn, "DP"):
        logger.info("Operation completed successfully")
        sys.exit(0)
    else:
        logger.error("Failed to update DisplayName")
        sys.exit(1)

if __name__ == "__main__":
    main()