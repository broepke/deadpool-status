#!/usr/bin/env python3
"""
Script to process all records by repeatedly invoking the Lambda function
until all records are processed.
"""

import json
import time
import argparse
import subprocess
import sys
import base64
from datetime import datetime

def run_command(command):
    """Run a shell command and return the output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        print(f"STDERR: {e.stderr}")
        sys.exit(1)

def invoke_lambda(function_name, payload=None):
    """Invoke the Lambda function with the given payload."""
    temp_file = "lambda_response.json"
    
    # Create payload file
    if payload:
        # Convert payload to JSON string with proper encoding
        payload_str = json.dumps(payload, default=str)
        # Write to a file to avoid command line escaping issues
        with open("lambda_payload.json", "w") as f:
            f.write(payload_str)
        cmd = f'aws lambda invoke --function-name {function_name} --payload fileb://lambda_payload.json {temp_file}'
    else:
        cmd = f'aws lambda invoke --function-name {function_name} --payload \'{{}}\' {temp_file}'
    
    # Invoke Lambda
    print(f"Invoking Lambda function: {function_name}")
    output = run_command(cmd)
    print(output)
    
    # Read response
    try:
        with open(temp_file, "r") as f:
            response = json.load(f)
        
        # Parse the body if it's a string
        if isinstance(response.get('body'), str):
            response['body'] = json.loads(response['body'])
        
        return response
    except Exception as e:
        print(f"Error reading Lambda response: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Process all records by invoking Lambda function repeatedly')
    parser.add_argument('--function-name', required=True, help='Lambda function name')
    parser.add_argument('--delay', type=int, default=5, help='Delay between Lambda invocations in seconds')
    parser.add_argument('--max-invocations', type=int, default=0, help='Maximum number of Lambda invocations (0 for unlimited)')
    args = parser.parse_args()
    
    function_name = args.function_name
    delay = args.delay
    max_invocations = args.max_invocations
    
    # Statistics
    total_processed = 0
    total_updated = 0
    total_failed = 0
    invocation_count = 0
    start_time = datetime.now()
    
    # Process all records
    pagination_token = None
    has_more_records = True
    
    print(f"Starting to process all records using Lambda function: {function_name}")
    print(f"Delay between invocations: {delay} seconds")
    if max_invocations > 0:
        print(f"Maximum invocations: {max_invocations}")
    print("-" * 80)
    
    while has_more_records:
        invocation_count += 1
        
        # Check if we've reached the maximum number of invocations
        if max_invocations > 0 and invocation_count > max_invocations:
            print(f"Reached maximum number of invocations ({max_invocations}). Stopping.")
            break
        
        print(f"\nInvocation #{invocation_count}")
        
        # Prepare payload with pagination token if available
        payload = None
        if pagination_token:
            # Handle different types of pagination tokens
            if isinstance(pagination_token, dict):
                # For the first invocation, the token is a dict
                payload = {"paginationToken": pagination_token}
                print(f"Using pagination token (dict): {json.dumps(pagination_token, default=str)}")
            elif isinstance(pagination_token, str):
                # For subsequent invocations, the token is a base64-encoded string
                try:
                    # Try to decode if it's base64-encoded
                    decoded_bytes = base64.b64decode(pagination_token)
                    decoded_str = decoded_bytes.decode('utf-8')
                    decoded_token = json.loads(decoded_str)
                    payload = {"paginationToken": decoded_token}
                    print(f"Using decoded pagination token: {json.dumps(decoded_token, default=str)}")
                except Exception as e:
                    # If not base64-encoded, use as is
                    payload = {"paginationToken": pagination_token}
                    print(f"Using pagination token (string): {pagination_token}")
            else:
                payload = {"paginationToken": str(pagination_token)}
                print(f"Using pagination token (other): {pagination_token}")
        
        # Invoke Lambda
        response = invoke_lambda(function_name, payload)
        
        # Extract statistics from response
        body = response.get('body', {})
        processed = body.get('processed', 0)
        updated = body.get('updated', 0)
        failed = body.get('failed', 0)
        duration = body.get('duration', 0)
        
        # Update totals
        total_processed += processed
        total_updated += updated
        total_failed += failed
        
        # Print statistics for this invocation
        print(f"Processed: {processed}, Updated: {updated}, Failed: {failed}, Duration: {duration:.2f}s")
        
        # Check if there are more records
        has_more_records = body.get('hasMoreRecords', False)
        pagination_token = body.get('paginationToken')
        
        if has_more_records:
            print(f"More records available. Waiting {delay} seconds before next invocation...")
            time.sleep(delay)
        else:
            print("No more records to process.")
    
    # Print final statistics
    total_duration = (datetime.now() - start_time).total_seconds()
    print("\n" + "=" * 80)
    print("Processing complete!")
    print(f"Total invocations: {invocation_count}")
    print(f"Total processed: {total_processed}")
    print(f"Total updated: {total_updated}")
    print(f"Total failed: {total_failed}")
    print(f"Total duration: {total_duration:.2f}s")
    print("=" * 80)

if __name__ == "__main__":
    main()