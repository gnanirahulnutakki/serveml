"""
AWS DynamoDB Integration Tests
"""
import pytest
import boto3
from boto3.dynamodb.conditions import Key, Attr
from moto import mock_dynamodb
from datetime import datetime, timedelta
import uuid


@mock_dynamodb
class TestDynamoDBIntegration:
    """Test DynamoDB integration"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup DynamoDB resources"""
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        self.dynamodb_client = boto3.client('dynamodb', region_name='us-east-1')
        
        # Create deployments table
        self.deployments_table = self.dynamodb.create_table(
            TableName='serveml-deployments',
            KeySchema=[
                {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                {'AttributeName': 'deployment_id', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'deployment_id', 'AttributeType': 'S'},
                {'AttributeName': 'created_at', 'AttributeType': 'S'},
                {'AttributeName': 'status', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'status-created_at-index',
                    'KeySchema': [
                        {'AttributeName': 'status', 'KeyType': 'HASH'},
                        {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'BillingMode': 'PAY_PER_REQUEST'
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Create users table
        self.users_table = self.dynamodb.create_table(
            TableName='serveml-users',
            KeySchema=[
                {'AttributeName': 'user_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'email', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'email-index',
                    'KeySchema': [
                        {'AttributeName': 'email', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'BillingMode': 'PAY_PER_REQUEST'
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
    
    def test_create_deployment(self):
        """Test creating deployment record"""
        deployment = {
            'user_id': 'test-user-123',
            'deployment_id': 'deploy-' + str(uuid.uuid4()),
            'name': 'test-model',
            'status': 'building',
            'created_at': datetime.utcnow().isoformat(),
            'model_metadata': {
                'framework': 'sklearn',
                'model_type': 'RandomForestClassifier',
                'size_mb': 1.5
            },
            's3_paths': {
                'model': 's3://serveml-models/test-user-123/deploy-123/model.pkl',
                'requirements': 's3://serveml-models/test-user-123/deploy-123/requirements.txt'
            }
        }
        
        response = self.deployments_table.put_item(Item=deployment)
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
    
    def test_query_user_deployments(self):
        """Test querying deployments by user"""
        user_id = 'test-user-456'
        
        # Create multiple deployments
        for i in range(5):
            deployment = {
                'user_id': user_id,
                'deployment_id': f'deploy-{i}',
                'name': f'model-{i}',
                'status': 'active' if i % 2 == 0 else 'building',
                'created_at': (datetime.utcnow() - timedelta(hours=i)).isoformat()
            }
            self.deployments_table.put_item(Item=deployment)
        
        # Query deployments
        response = self.deployments_table.query(
            KeyConditionExpression=Key('user_id').eq(user_id),
            ScanIndexForward=False  # Sort by newest first
        )
        
        assert response['Count'] == 5
        assert all(item['user_id'] == user_id for item in response['Items'])
    
    def test_update_deployment_status(self):
        """Test updating deployment status"""
        user_id = 'test-user-789'
        deployment_id = 'deploy-update-test'
        
        # Create deployment
        self.deployments_table.put_item(Item={
            'user_id': user_id,
            'deployment_id': deployment_id,
            'status': 'building',
            'created_at': datetime.utcnow().isoformat()
        })
        
        # Update status
        response = self.deployments_table.update_item(
            Key={
                'user_id': user_id,
                'deployment_id': deployment_id
            },
            UpdateExpression='SET #status = :status, updated_at = :updated_at',
            ExpressionAttributeNames={
                '#status': 'status'
            },
            ExpressionAttributeValues={
                ':status': 'active',
                ':updated_at': datetime.utcnow().isoformat()
            },
            ReturnValues='ALL_NEW'
        )
        
        assert response['Attributes']['status'] == 'active'
        assert 'updated_at' in response['Attributes']
    
    def test_batch_write_deployments(self):
        """Test batch writing multiple deployments"""
        items = []
        for i in range(25):  # DynamoDB batch limit
            items.append({
                'PutRequest': {
                    'Item': {
                        'user_id': {'S': f'batch-user-{i % 5}'},
                        'deployment_id': {'S': f'batch-deploy-{i}'},
                        'status': {'S': 'active'},
                        'created_at': {'S': datetime.utcnow().isoformat()}
                    }
                }
            })
        
        response = self.dynamodb_client.batch_write_item(
            RequestItems={
                'serveml-deployments': items
            }
        )
        
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
    
    def test_scan_with_filter(self):
        """Test scanning table with filters"""
        # Add test data
        for i in range(10):
            self.deployments_table.put_item(Item={
                'user_id': f'scan-user-{i}',
                'deployment_id': f'scan-deploy-{i}',
                'status': 'active' if i < 5 else 'failed',
                'framework': 'sklearn' if i % 2 == 0 else 'pytorch',
                'created_at': datetime.utcnow().isoformat()
            })
        
        # Scan for failed deployments
        response = self.deployments_table.scan(
            FilterExpression=Attr('status').eq('failed')
        )
        
        assert response['Count'] == 5
        assert all(item['status'] == 'failed' for item in response['Items'])
    
    def test_gsi_query(self):
        """Test querying Global Secondary Index"""
        # Add test data
        for i in range(10):
            self.deployments_table.put_item(Item={
                'user_id': f'gsi-user-{i}',
                'deployment_id': f'gsi-deploy-{i}',
                'status': 'active',
                'created_at': (datetime.utcnow() - timedelta(hours=i)).isoformat()
            })
        
        # Query GSI for active deployments
        response = self.deployments_table.query(
            IndexName='status-created_at-index',
            KeyConditionExpression=Key('status').eq('active'),
            ScanIndexForward=False,
            Limit=5
        )
        
        assert response['Count'] == 5
        assert all(item['status'] == 'active' for item in response['Items'])
    
    def test_conditional_writes(self):
        """Test conditional writes to prevent overwrites"""
        user_id = 'conditional-user'
        deployment_id = 'conditional-deploy'
        
        # Initial write
        self.deployments_table.put_item(Item={
            'user_id': user_id,
            'deployment_id': deployment_id,
            'status': 'building',
            'version': 1
        })
        
        # Try to update only if version matches
        try:
            self.deployments_table.update_item(
                Key={
                    'user_id': user_id,
                    'deployment_id': deployment_id
                },
                UpdateExpression='SET #status = :status, version = :new_version',
                ConditionExpression='version = :expected_version',
                ExpressionAttributeNames={
                    '#status': 'status'
                },
                ExpressionAttributeValues={
                    ':status': 'active',
                    ':new_version': 2,
                    ':expected_version': 1
                }
            )
            success = True
        except Exception:
            success = False
        
        assert success
    
    def test_ttl_configuration(self):
        """Test Time-To-Live configuration"""
        # Enable TTL on deployments table
        response = self.dynamodb_client.update_time_to_live(
            TableName='serveml-deployments',
            TimeToLiveSpecification={
                'AttributeName': 'ttl',
                'Enabled': True
            }
        )
        
        assert response['TimeToLiveSpecification']['AttributeName'] == 'ttl'
        assert response['TimeToLiveSpecification']['TimeToLiveStatus'] in ['ENABLING', 'ENABLED']
    
    def test_point_in_time_recovery(self):
        """Test enabling point-in-time recovery"""
        response = self.dynamodb_client.update_continuous_backups(
            TableName='serveml-deployments',
            PointInTimeRecoverySpecification={
                'PointInTimeRecoveryEnabled': True
            }
        )
        
        assert response['ContinuousBackupsDescription']['PointInTimeRecoveryDescription']['PointInTimeRecoveryStatus'] in ['ENABLING', 'ENABLED']
    
    def test_create_user(self):
        """Test creating user record"""
        user = {
            'user_id': str(uuid.uuid4()),
            'email': 'test@serveml.com',
            'username': 'testuser',
            'created_at': datetime.utcnow().isoformat(),
            'deployment_count': 0,
            'total_requests': 0
        }
        
        response = self.users_table.put_item(Item=user)
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200
    
    def test_query_user_by_email(self):
        """Test querying user by email using GSI"""
        email = 'query@serveml.com'
        user_id = str(uuid.uuid4())
        
        # Create user
        self.users_table.put_item(Item={
            'user_id': user_id,
            'email': email,
            'username': 'queryuser'
        })
        
        # Query by email
        response = self.users_table.query(
            IndexName='email-index',
            KeyConditionExpression=Key('email').eq(email)
        )
        
        assert response['Count'] == 1
        assert response['Items'][0]['user_id'] == user_id