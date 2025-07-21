"""
Pytest configuration and shared fixtures
"""
import pytest
import tempfile
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from fastapi.testclient import TestClient
from app import app
import boto3
from moto import mock_s3, mock_dynamodb


@pytest.fixture
def test_client():
    """Create test client for FastAPI app"""
    return TestClient(app)


@pytest.fixture
def auth_headers(test_client):
    """Get authentication headers for testing"""
    # Register a test user
    response = test_client.post("/api/v1/auth/register", json={
        "email": "test@serveml.com",
        "username": "testuser",
        "password": "testpass123"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_model_file():
    """Create a test model file"""
    import pickle
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.datasets import load_iris
    
    with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as f:
        X, y = load_iris(return_X_y=True)
        model = RandomForestClassifier(n_estimators=10)
        model.fit(X, y)
        pickle.dump(model, f)
        yield f.name
    
    # Cleanup
    os.unlink(f.name)


@pytest.fixture
def test_requirements_file():
    """Create a test requirements file"""
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False, mode='w') as f:
        f.write("scikit-learn==1.3.0\n")
        f.write("numpy==1.24.3\n")
        yield f.name
    
    # Cleanup
    os.unlink(f.name)


@pytest.fixture
def mock_aws_services():
    """Mock AWS services for testing"""
    with mock_s3(), mock_dynamodb():
        # Create mock S3 bucket
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='serveml-test-bucket')
        
        # Create mock DynamoDB tables
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Deployments table
        dynamodb.create_table(
            TableName='serveml-deployments',
            KeySchema=[
                {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                {'AttributeName': 'deployment_id', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'deployment_id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        yield {
            's3': s3,
            'dynamodb': dynamodb
        }


@pytest.fixture
def sample_deployment_data():
    """Sample deployment data for testing"""
    return {
        "id": "test-deployment-123",
        "name": "test-model",
        "user_id": "test-user-123",
        "status": "active",
        "created_at": "2025-01-21T12:00:00Z",
        "model_metadata": {
            "framework": "sklearn",
            "model_type": "RandomForestClassifier",
            "input_shape": (4,),
            "size_mb": 0.5
        }
    }