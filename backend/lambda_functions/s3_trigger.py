"""
S3 Event Trigger Lambda Function
Triggers GitHub Actions workflow when model files are uploaded to S3
"""
import json
import os
import boto3
import urllib3
from typing import Dict, Any
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Environment variables
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
GITHUB_OWNER = os.environ.get('GITHUB_OWNER', 'gnanirahulnutakki')
GITHUB_REPO = os.environ.get('GITHUB_REPO', 'serveml')
DEPLOYMENTS_TABLE = os.environ.get('DEPLOYMENTS_TABLE', 'serveml-deployments')

# Initialize HTTP client
http = urllib3.PoolManager()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle S3 PUT events and trigger deployment workflow
    
    Expected S3 structure:
    - s3://bucket/deployments/{deployment_id}/model.pkl
    - s3://bucket/deployments/{deployment_id}/requirements.txt
    """
    try:
        # Parse S3 event
        for record in event['Records']:
            # Get S3 event details
            s3_event = record['s3']
            bucket_name = s3_event['bucket']['name']
            object_key = s3_event['object']['key']
            
            logger.info(f"Processing S3 event: {bucket_name}/{object_key}")
            
            # Extract deployment ID from path
            # Expected format: deployments/{deployment_id}/filename
            path_parts = object_key.split('/')
            if len(path_parts) < 3 or path_parts[0] != 'deployments':
                logger.warning(f"Ignoring non-deployment file: {object_key}")
                continue
            
            deployment_id = path_parts[1]
            filename = path_parts[2]
            
            # Check if this is a trigger file (both files uploaded)
            if filename == 'trigger.json':
                logger.info(f"Trigger file detected for deployment: {deployment_id}")
                
                # Read trigger file for metadata
                trigger_obj = s3_client.get_object(Bucket=bucket_name, Key=object_key)
                trigger_data = json.loads(trigger_obj['Body'].read())
                
                # Verify both required files exist
                model_key = f"deployments/{deployment_id}/model.pkl"
                requirements_key = f"deployments/{deployment_id}/requirements.txt"
                
                try:
                    s3_client.head_object(Bucket=bucket_name, Key=model_key)
                    s3_client.head_object(Bucket=bucket_name, Key=requirements_key)
                except Exception as e:
                    logger.error(f"Required files not found: {e}")
                    update_deployment_status(deployment_id, 'failed', 
                                           error='Required files not found')
                    continue
                
                # Update deployment status
                update_deployment_status(deployment_id, 'building')
                
                # Trigger GitHub Actions workflow
                success = trigger_github_workflow(
                    deployment_id=deployment_id,
                    model_path=model_key,
                    requirements_path=requirements_key,
                    framework=trigger_data.get('framework', 'sklearn')
                )
                
                if not success:
                    update_deployment_status(deployment_id, 'failed', 
                                           error='Failed to trigger deployment workflow')
        
        return {
            'statusCode': 200,
            'body': json.dumps('S3 events processed successfully')
        }
        
    except Exception as e:
        logger.error(f"Error processing S3 event: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }


def trigger_github_workflow(deployment_id: str, model_path: str, 
                          requirements_path: str, framework: str) -> bool:
    """
    Trigger GitHub Actions workflow via API
    """
    try:
        # Prepare workflow dispatch payload
        workflow_payload = {
            "ref": "main",
            "inputs": {
                "deployment_id": deployment_id,
                "model_path": model_path,
                "requirements_path": requirements_path,
                "framework": framework
            }
        }
        
        # GitHub API endpoint
        url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/workflows/deploy_model.yml/dispatches"
        
        # Make request
        response = http.request(
            'POST',
            url,
            body=json.dumps(workflow_payload),
            headers={
                'Authorization': f'token {GITHUB_TOKEN}',
                'Accept': 'application/vnd.github.v3+json',
                'Content-Type': 'application/json',
                'User-Agent': 'ServeML-Lambda'
            }
        )
        
        if response.status == 204:
            logger.info(f"Successfully triggered workflow for deployment: {deployment_id}")
            return True
        else:
            logger.error(f"Failed to trigger workflow: {response.status} - {response.data}")
            return False
            
    except Exception as e:
        logger.error(f"Error triggering GitHub workflow: {str(e)}")
        return False


def update_deployment_status(deployment_id: str, status: str, 
                            error: str = None, endpoint_url: str = None):
    """
    Update deployment status in DynamoDB
    """
    try:
        table = dynamodb.Table(DEPLOYMENTS_TABLE)
        
        # Prepare update expression
        update_expr = "SET #status = :status, updated_at = :timestamp"
        expr_values = {
            ':status': status,
            ':timestamp': boto3.dynamodb.types.TypeSerializer().serialize(
                datetime.utcnow().isoformat()
            )
        }
        expr_names = {'#status': 'status'}
        
        if error:
            update_expr += ", error_message = :error"
            expr_values[':error'] = error
            
        if endpoint_url:
            update_expr += ", endpoint_url = :url"
            expr_values[':url'] = endpoint_url
        
        # Update item
        table.update_item(
            Key={'deployment_id': deployment_id},
            UpdateExpression=update_expr,
            ExpressionAttributeValues=expr_values,
            ExpressionAttributeNames=expr_names
        )
        
        logger.info(f"Updated deployment {deployment_id} status to: {status}")
        
    except Exception as e:
        logger.error(f"Error updating deployment status: {str(e)}")


# For local testing
if __name__ == "__main__":
    # Test event
    test_event = {
        "Records": [{
            "s3": {
                "bucket": {"name": "serveml-uploads"},
                "object": {"key": "deployments/test-123/trigger.json"}
            }
        }]
    }
    
    # Set test environment
    os.environ['GITHUB_TOKEN'] = 'test-token'
    
    # Test handler
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))