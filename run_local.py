import json
import os
import sys
sys.path.append('src')

# Set required environment variables
os.environ['TABLE_NAME'] = 'Deadpool'
os.environ['LOG_LEVEL'] = 'INFO'
os.environ['BATCH_SIZE'] = '25'

from lambda_function import lambda_handler

def main():
    with open('events/schedule.json') as f:
        event = json.load(f)
    
    context = type('Context', (), {
        'log_stream_name': 'local',
        'function_name': 'DeadpoolStatusChecker'
    })()
    
    try:
        result = lambda_handler(event, context)
        print("\nLambda execution completed successfully!")
        print(f"Result: {json.dumps(result, indent=2)}")
    except KeyboardInterrupt:
        print("\nExecution interrupted by user")
    except Exception as e:
        print(f"\nError during execution: {e}")

if __name__ == '__main__':
    main()