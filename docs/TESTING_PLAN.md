# ServeML Comprehensive Testing Plan

## Table of Contents
1. [Testing Overview](#testing-overview)
2. [Test Types & Strategies](#test-types--strategies)
3. [Local Testing Phase](#local-testing-phase)
4. [AWS Testing Phase](#aws-testing-phase)
5. [Test Data & Models](#test-data--models)
6. [AWS Requirements](#aws-requirements)
7. [Cost Estimates](#cost-estimates)
8. [Test Automation](#test-automation)
9. [Performance Benchmarks](#performance-benchmarks)
10. [Security Testing](#security-testing)

---

## Testing Overview

ServeML requires thorough testing across multiple layers:
- **Local Development Testing**: No AWS costs, rapid iteration
- **AWS Integration Testing**: Real infrastructure, actual costs
- **End-to-End Testing**: Complete user journey validation
- **Load Testing**: Scalability and performance validation

### Testing Timeline
- **Week 1**: Local testing and unit tests
- **Week 2**: AWS infrastructure setup and integration tests
- **Week 3**: End-to-end and load testing
- **Week 4**: Security testing and production readiness

---

## Test Types & Strategies

### 1. Unit Tests
**Scope**: Individual functions and classes
**Tools**: pytest, pytest-cov, unittest.mock

```python
# Test Categories:
- Model validation logic
- Docker builder functions
- Authentication services
- Metrics calculations
- S3 service operations
```

### 2. Integration Tests
**Scope**: Component interactions
**Tools**: pytest, httpx, moto (AWS mocking)

```python
# Test Categories:
- API endpoint integration
- Database operations
- S3 file uploads
- Authentication flow
- Deployment pipeline
```

### 3. End-to-End Tests
**Scope**: Complete user workflows
**Tools**: Selenium/Playwright, pytest

```python
# Test Scenarios:
- User registration → login → deploy model → test prediction
- Model upload → validation → deployment → monitoring
- Multiple model deployments
- Model deletion and cleanup
```

### 4. Load Tests
**Scope**: Performance and scalability
**Tools**: Locust, k6, Apache JMeter

```python
# Test Scenarios:
- Concurrent model deployments (10, 50, 100)
- Prediction endpoint load (1000, 10000 req/sec)
- Large model uploads (100MB, 500MB)
- Sustained load over time
```

### 5. Security Tests
**Scope**: Vulnerability assessment
**Tools**: OWASP ZAP, Bandit, Safety

```python
# Test Areas:
- Authentication bypass attempts
- SQL/NoSQL injection
- File upload vulnerabilities
- API rate limiting
- Token security
```

---

## Local Testing Phase

### Setup Requirements
```bash
# 1. Install dependencies
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt

# 2. Run local services
docker-compose up -d

# 3. Set environment variables
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1
```

### Local Test Suite

#### 1. Backend Unit Tests
```bash
# Run all unit tests
pytest backend/tests -v --cov=backend --cov-report=html

# Run specific test categories
pytest backend/tests/test_model_validator.py -v
pytest backend/tests/test_docker_builder.py -v
pytest backend/tests/test_auth.py -v
```

#### 2. API Integration Tests
```python
# backend/tests/test_api_integration.py
import pytest
from fastapi.testclient import TestClient
from app import app

class TestAPIIntegration:
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_complete_deployment_flow(self, client):
        # 1. Register user
        response = client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "testpass123"
        })
        assert response.status_code == 200
        token = response.json()["access_token"]
        
        # 2. Upload model
        files = {
            "model_file": ("model.pkl", open("test_models/iris_model.pkl", "rb")),
            "requirements_file": ("requirements.txt", open("test_models/requirements.txt", "rb"))
        }
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.post("/api/v1/deploy", files=files, headers=headers)
        assert response.status_code == 200
        deployment_id = response.json()["id"]
        
        # 3. Check deployment status
        response = client.get(f"/api/v1/deployments/{deployment_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["status"] in ["validating", "building", "deploying"]
```

#### 3. Frontend Tests
```javascript
// frontend/tests/app.test.js
describe('ServeML Frontend', () => {
    test('Upload form renders correctly', () => {
        // Test form elements exist
    });
    
    test('File validation works', () => {
        // Test file type validation
    });
    
    test('Deployment status updates', () => {
        // Test polling mechanism
    });
});
```

### Local Docker Testing
```bash
# Build and test model serving container
cd backend
docker build -f templates/Dockerfile -t serveml-test .
docker run -p 9000:8080 serveml-test

# Test Lambda function locally
curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" \
  -d '{"body": "{\"data\": [5.1, 3.5, 1.4, 0.2]}"}'
```

---

## AWS Testing Phase

### Infrastructure Testing

#### 1. Terraform Validation
```bash
cd infrastructure
terraform init
terraform validate
terraform plan -var-file=test.tfvars

# Dry run with specific resources
terraform plan -target=aws_s3_bucket.uploads
terraform plan -target=aws_dynamodb_table.deployments
```

#### 2. Progressive Deployment
```bash
# Stage 1: Core infrastructure only
terraform apply -target=aws_s3_bucket.uploads \
                -target=aws_dynamodb_table.deployments \
                -target=aws_ecr_repository.models

# Stage 2: IAM and Lambda
terraform apply -target=aws_iam_role.lambda_execution \
                -target=aws_lambda_function.s3_trigger

# Stage 3: Full deployment
terraform apply
```

### Integration Testing on AWS

#### 1. S3 Upload Test
```python
# tests/aws/test_s3_integration.py
import boto3
import pytest

class TestS3Integration:
    @pytest.fixture
    def s3_client(self):
        return boto3.client('s3', region_name='us-east-1')
    
    def test_model_upload(self, s3_client):
        bucket_name = "serveml-uploads-test-123456789"
        
        # Upload test model
        s3_client.upload_file(
            'test_models/iris_model.pkl',
            bucket_name,
            'deployments/test-123/model.pkl'
        )
        
        # Verify upload
        response = s3_client.head_object(
            Bucket=bucket_name,
            Key='deployments/test-123/model.pkl'
        )
        assert response['ContentLength'] > 0
```

#### 2. Lambda Function Test
```python
# tests/aws/test_lambda_integration.py
import boto3
import json

class TestLambdaIntegration:
    @pytest.fixture
    def lambda_client(self):
        return boto3.client('lambda', region_name='us-east-1')
    
    def test_s3_trigger_lambda(self, lambda_client):
        # Invoke Lambda function
        response = lambda_client.invoke(
            FunctionName='serveml-s3-trigger-test',
            InvocationType='RequestResponse',
            Payload=json.dumps({
                "Records": [{
                    "s3": {
                        "bucket": {"name": "serveml-uploads-test"},
                        "object": {"key": "deployments/test-123/trigger.json"}
                    }
                }]
            })
        )
        
        assert response['StatusCode'] == 200
```

#### 3. End-to-End AWS Test
```bash
# Deploy a real model through the system
./tests/aws/e2e_test.sh

# Script contents:
#!/bin/bash
# 1. Upload model to S3
aws s3 cp test_models/iris_model.pkl s3://serveml-uploads-test/deployments/e2e-test/model.pkl
aws s3 cp test_models/requirements.txt s3://serveml-uploads-test/deployments/e2e-test/requirements.txt

# 2. Trigger deployment
aws s3 cp tests/trigger.json s3://serveml-uploads-test/deployments/e2e-test/trigger.json

# 3. Wait and check Lambda creation
sleep 60
aws lambda get-function --function-name serveml-e2e-test

# 4. Test prediction endpoint
curl -X POST https://api-id.execute-api.us-east-1.amazonaws.com/v1/predict \
  -H "Content-Type: application/json" \
  -d '{"data": [5.1, 3.5, 1.4, 0.2]}'
```

---

## Test Data & Models

### 1. Sample Models

```python
# tests/create_test_models.py
import pickle
import torch
import tensorflow as tf
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.datasets import load_iris, load_digits
import joblib

def create_sklearn_models():
    """Create various sklearn models for testing"""
    X, y = load_iris(return_X_y=True)
    
    # Small model (~1KB)
    small_model = LogisticRegression()
    small_model.fit(X, y)
    with open('test_models/small_model.pkl', 'wb') as f:
        pickle.dump(small_model, f)
    
    # Medium model (~1MB)
    medium_model = RandomForestClassifier(n_estimators=100)
    medium_model.fit(X, y)
    joblib.dump(medium_model, 'test_models/medium_model.pkl')
    
    # Large model simulation (~50MB)
    X_large, y_large = load_digits(return_X_y=True)
    large_model = RandomForestClassifier(n_estimators=1000)
    large_model.fit(X_large, y_large)
    joblib.dump(large_model, 'test_models/large_model.pkl', compress=3)

def create_pytorch_models():
    """Create PyTorch models for testing"""
    class SimpleNN(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.fc1 = torch.nn.Linear(4, 10)
            self.fc2 = torch.nn.Linear(10, 3)
        
        def forward(self, x):
            x = torch.relu(self.fc1(x))
            return self.fc2(x)
    
    model = SimpleNN()
    torch.save(model, 'test_models/pytorch_model.pt')

def create_tensorflow_models():
    """Create TensorFlow models for testing"""
    model = tf.keras.Sequential([
        tf.keras.layers.Dense(10, activation='relu', input_shape=(4,)),
        tf.keras.layers.Dense(3, activation='softmax')
    ])
    model.compile(optimizer='adam', loss='sparse_categorical_crossentropy')
    model.save('test_models/tensorflow_model.h5')
```

### 2. Test Requirements Files

```python
# tests/create_requirements_files.py
test_requirements = {
    "minimal": "scikit-learn==1.3.0\nnumpy==1.24.3",
    "pytorch": "torch==2.0.1\ntorchvision==0.15.2\nnumpy==1.24.3",
    "tensorflow": "tensorflow==2.13.0\nnumpy==1.24.3",
    "complex": """scikit-learn==1.3.0
pandas==2.0.3
numpy==1.24.3
scipy==1.11.1
matplotlib==3.7.2
seaborn==0.12.2
xgboost==1.7.6""",
    "invalid": "nonexistent-package==1.0.0\nbroken_requirement"
}

for name, content in test_requirements.items():
    with open(f'test_models/requirements_{name}.txt', 'w') as f:
        f.write(content)
```

### 3. Load Test Data

```python
# tests/load_test_data.py
import json
import numpy as np

# Generate prediction payloads of various sizes
payloads = {
    "small": {"data": [5.1, 3.5, 1.4, 0.2]},
    "medium": {"data": np.random.rand(100).tolist()},
    "large": {"data": np.random.rand(1000).tolist()},
    "xlarge": {"data": np.random.rand(10000).tolist()}
}

for size, payload in payloads.items():
    with open(f'test_data/payload_{size}.json', 'w') as f:
        json.dump(payload, f)
```

---

## AWS Requirements

### Required AWS Services

| Service | Purpose | Required Permissions |
|---------|---------|---------------------|
| **S3** | Model storage | CreateBucket, PutObject, GetObject, DeleteObject |
| **DynamoDB** | Metadata storage | CreateTable, PutItem, GetItem, Query |
| **Lambda** | Model serving | CreateFunction, UpdateFunction, InvokeFunction |
| **ECR** | Container registry | CreateRepository, PutImage, GetImage |
| **API Gateway** | HTTP endpoints | CreateApi, CreateRoute, CreateStage |
| **CloudWatch** | Logs & metrics | PutMetricData, CreateLogGroup |
| **IAM** | Access control | CreateRole, AttachPolicy |
| **Secrets Manager** | GitHub token | CreateSecret, GetSecretValue |

### Minimum IAM Permissions for Testing

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:*",
        "dynamodb:*",
        "lambda:*",
        "ecr:*",
        "apigateway:*",
        "iam:*",
        "logs:*",
        "cloudwatch:*",
        "secretsmanager:*"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "us-east-1"
        }
      }
    }
  ]
}
```

### AWS Account Setup

1. **Create Testing Account**
   - Use AWS Organizations for isolated testing
   - Enable Cost Explorer
   - Set up billing alerts

2. **Configure Service Quotas**
   - Lambda concurrent executions: 100
   - S3 buckets: 10
   - DynamoDB tables: 10

3. **Enable Required Services**
   - Lambda container support
   - API Gateway HTTP APIs
   - ECR scanning

---

## Cost Estimates

### Testing Phase Costs (Monthly)

#### Local Testing
- **Cost**: $0
- **Duration**: 1 week
- **Resources**: Local Docker, mock AWS services

#### AWS Integration Testing

| Resource | Usage | Hourly Cost | Daily Cost | Weekly Cost |
|----------|-------|-------------|------------|-------------|
| **S3** | 10GB storage, 1000 requests/day | $0.001 | $0.03 | $0.21 |
| **DynamoDB** | 1000 writes/day, 5000 reads/day | $0.002 | $0.05 | $0.35 |
| **Lambda** | 1000 invocations/day, 3GB-seconds each | $0.02 | $0.50 | $3.50 |
| **ECR** | 5GB storage | $0.01 | $0.25 | $1.75 |
| **API Gateway** | 10000 requests/day | $0.004 | $0.10 | $0.70 |
| **CloudWatch** | Logs and metrics | $0.02 | $0.50 | $3.50 |
| **Data Transfer** | 1GB/day | $0.004 | $0.09 | $0.63 |

**Total Weekly Cost**: ~$10.64
**Total Monthly Cost**: ~$45

#### Load Testing Costs

| Test Type | Duration | Resources | Estimated Cost |
|-----------|----------|-----------|----------------|
| **Light Load** | 1 hour | 100 req/sec | $5 |
| **Medium Load** | 1 hour | 1000 req/sec | $25 |
| **Heavy Load** | 1 hour | 10000 req/sec | $100 |
| **Sustained Test** | 24 hours | 100 req/sec | $50 |

#### Cost Optimization Tips

1. **Use AWS Free Tier**
   - 1M Lambda requests/month free
   - 5GB S3 storage free
   - 25GB DynamoDB storage free

2. **Cleanup Resources**
   ```bash
   # Destroy test infrastructure after each session
   terraform destroy -auto-approve
   ```

3. **Use Spot Instances** for load testing
4. **Set up budget alerts** at $50, $100, $200

### Total Testing Budget

| Phase | Duration | Estimated Cost |
|-------|----------|----------------|
| **Local Testing** | 1 week | $0 |
| **AWS Integration** | 2 weeks | $90 |
| **Load Testing** | 1 week | $200 |
| **Security Testing** | 1 week | $50 |
| **Buffer** | - | $60 |
| **Total** | 4 weeks | **$400** |

---

## Test Automation

### 1. Continuous Integration Tests

```yaml
# .github/workflows/test.yml additions
test-integration:
  runs-on: ubuntu-latest
  services:
    localstack:
      image: localstack/localstack
      ports:
        - 4566:4566
      env:
        SERVICES: s3,dynamodb,lambda
  
  steps:
    - uses: actions/checkout@v4
    - name: Run integration tests
      run: |
        export AWS_ENDPOINT_URL=http://localhost:4566
        pytest tests/integration -v
```

### 2. Nightly E2E Tests

```yaml
# .github/workflows/nightly.yml
name: Nightly E2E Tests
on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM UTC daily

jobs:
  e2e-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy test infrastructure
        run: |
          cd infrastructure
          terraform apply -auto-approve -var="environment=test"
      
      - name: Run E2E tests
        run: |
          python tests/e2e/full_deployment_test.py
      
      - name: Cleanup
        if: always()
        run: |
          cd infrastructure
          terraform destroy -auto-approve
```

### 3. Load Test Automation

```python
# tests/load/locustfile.py
from locust import HttpUser, task, between

class ServeMLUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # Login
        response = self.client.post("/api/v1/auth/login", json={
            "email": "loadtest@example.com",
            "password": "loadtest123"
        })
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(1)
    def list_deployments(self):
        self.client.get("/api/v1/deployments", headers=self.headers)
    
    @task(2)
    def get_deployment_status(self):
        self.client.get("/api/v1/deployments/test-deployment-1", headers=self.headers)
    
    @task(5)
    def make_prediction(self):
        self.client.post(
            "/api/v1/test-model",
            json={
                "deployment_id": "test-deployment-1",
                "data": [5.1, 3.5, 1.4, 0.2]
            },
            headers=self.headers
        )
```

---

## Performance Benchmarks

### Expected Performance Metrics

| Metric | Target | Acceptable | Critical |
|--------|--------|------------|----------|
| **API Response Time** | <100ms | <500ms | >1000ms |
| **Model Load Time** | <2s | <5s | >10s |
| **Cold Start** | <3s | <10s | >15s |
| **Deployment Time** | <2min | <5min | >10min |
| **Concurrent Users** | 1000 | 500 | 100 |
| **Predictions/sec** | 1000 | 500 | 100 |

### Performance Test Scripts

```python
# tests/performance/benchmark.py
import time
import statistics
import concurrent.futures
import requests

class PerformanceBenchmark:
    def __init__(self, base_url):
        self.base_url = base_url
        self.results = []
    
    def test_prediction_latency(self, num_requests=1000):
        """Test prediction endpoint latency"""
        latencies = []
        
        for _ in range(num_requests):
            start = time.time()
            response = requests.post(
                f"{self.base_url}/predict",
                json={"data": [5.1, 3.5, 1.4, 0.2]}
            )
            latencies.append((time.time() - start) * 1000)
        
        return {
            "mean": statistics.mean(latencies),
            "median": statistics.median(latencies),
            "p95": statistics.quantiles(latencies, n=20)[18],
            "p99": statistics.quantiles(latencies, n=100)[98]
        }
    
    def test_concurrent_load(self, num_users=100, requests_per_user=10):
        """Test concurrent user load"""
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = []
            start_time = time.time()
            
            for _ in range(num_users):
                future = executor.submit(
                    self._make_requests, requests_per_user
                )
                futures.append(future)
            
            results = [f.result() for f in futures]
            total_time = time.time() - start_time
            
        return {
            "total_requests": num_users * requests_per_user,
            "total_time": total_time,
            "requests_per_second": (num_users * requests_per_user) / total_time,
            "success_rate": sum(r["success"] for r in results) / len(results) * 100
        }
```

---

## Security Testing

### 1. Vulnerability Scanning

```bash
# Static code analysis
bandit -r backend/ -f json -o security_report.json

# Dependency scanning
safety check -r backend/requirements.txt

# Docker image scanning
docker scan serveml-model:latest

# AWS security scanning
prowler -g cis_level2_aws
```

### 2. Penetration Testing

```python
# tests/security/test_auth_bypass.py
class TestAuthSecurity:
    def test_missing_token(self, client):
        """Test endpoints without authentication"""
        response = client.get("/api/v1/deployments")
        assert response.status_code == 401
    
    def test_invalid_token(self, client):
        """Test with invalid JWT token"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/v1/deployments", headers=headers)
        assert response.status_code == 401
    
    def test_expired_token(self, client):
        """Test with expired JWT token"""
        # Create token with past expiration
        expired_token = create_expired_token()
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/api/v1/deployments", headers=headers)
        assert response.status_code == 401
```

### 3. Input Validation Testing

```python
# tests/security/test_input_validation.py
class TestInputValidation:
    def test_sql_injection(self, client):
        """Test SQL injection attempts"""
        payloads = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--"
        ]
        
        for payload in payloads:
            response = client.post("/api/v1/auth/login", json={
                "email": payload,
                "password": "test"
            })
            assert response.status_code in [400, 401]
    
    def test_file_upload_validation(self, client):
        """Test malicious file uploads"""
        # Test oversized file
        large_file = io.BytesIO(b"0" * (600 * 1024 * 1024))  # 600MB
        files = {"model_file": ("large.pkl", large_file)}
        response = client.post("/api/v1/deploy", files=files)
        assert response.status_code == 413
        
        # Test wrong file type
        files = {"model_file": ("malicious.exe", b"MZ\x90\x00")}
        response = client.post("/api/v1/deploy", files=files)
        assert response.status_code == 400
```

---

## Test Execution Schedule

### Week 1: Local Development Testing
- **Day 1-2**: Unit tests, code coverage
- **Day 3-4**: Integration tests with mocked AWS
- **Day 5**: Docker container testing

### Week 2: AWS Infrastructure Testing  
- **Day 1**: Terraform validation and planning
- **Day 2-3**: Progressive infrastructure deployment
- **Day 4-5**: Service integration testing

### Week 3: End-to-End Testing
- **Day 1-2**: Full deployment workflow testing
- **Day 3-4**: Load and performance testing
- **Day 5**: Test result analysis

### Week 4: Security & Production Readiness
- **Day 1-2**: Security vulnerability testing
- **Day 3**: Penetration testing
- **Day 4**: Documentation and cleanup
- **Day 5**: Final test report

---

## Success Criteria

### Functional Requirements
- [ ] All unit tests pass (>90% coverage)
- [ ] All integration tests pass
- [ ] E2E deployment works for all model types
- [ ] Authentication and authorization work correctly
- [ ] Metrics and monitoring function properly

### Non-Functional Requirements
- [ ] API response time <500ms (p95)
- [ ] Support 100 concurrent users
- [ ] No critical security vulnerabilities
- [ ] Infrastructure costs <$50/month for MVP
- [ ] Deployment time <5 minutes

### Production Readiness Checklist
- [ ] All tests automated in CI/CD
- [ ] Monitoring and alerting configured
- [ ] Disaster recovery plan tested
- [ ] Documentation complete
- [ ] Security review passed