# ServeML Troubleshooting Guide

This guide helps diagnose and resolve common issues with ServeML deployments.

## Table of Contents

1. [Common Issues](#common-issues)
2. [Deployment Problems](#deployment-problems)
3. [Prediction Errors](#prediction-errors)
4. [Performance Issues](#performance-issues)
5. [Infrastructure Problems](#infrastructure-problems)
6. [Security Issues](#security-issues)
7. [Debugging Tools](#debugging-tools)
8. [Support Escalation](#support-escalation)

## Common Issues

### Authentication Failures

#### Symptom: 401 Unauthorized Error
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Invalid or expired token"
  }
}
```

**Causes:**
- Expired JWT token
- Invalid token format
- Token not included in request

**Solutions:**

1. **Check token expiration:**
```python
import jwt
from datetime import datetime

def check_token(token):
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        exp = datetime.fromtimestamp(payload['exp'])
        print(f"Token expires at: {exp}")
        print(f"Current time: {datetime.now()}")
        return exp > datetime.now()
    except:
        return False
```

2. **Refresh token:**
```bash
# Get new token
curl -X POST https://api.serveml.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "password": "your-password"}'
```

3. **Verify header format:**
```bash
# Correct format
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...

# Common mistakes
Authorization: eyJ0eXAiOiJKV1QiLCJhbGc...  # Missing "Bearer"
Authorization: Bearer: eyJ0eXAiOiJKV1QiLCJhbGc...  # Extra colon
```

### Rate Limiting

#### Symptom: 429 Too Many Requests
```json
{
  "error": {
    "code": "RATE_LIMITED",
    "message": "Rate limit exceeded",
    "retry_after": 60
  }
}
```

**Solutions:**

1. **Check rate limit headers:**
```python
response = requests.get(url, headers=headers)
print(f"Limit: {response.headers.get('X-RateLimit-Limit')}")
print(f"Remaining: {response.headers.get('X-RateLimit-Remaining')}")
print(f"Reset: {response.headers.get('X-RateLimit-Reset')}")
```

2. **Implement exponential backoff:**
```python
import time
import random

def retry_with_backoff(func, max_retries=5):
    for i in range(max_retries):
        try:
            return func()
        except RateLimitError as e:
            if i == max_retries - 1:
                raise
            wait_time = (2 ** i) + random.uniform(0, 1)
            time.sleep(wait_time)
```

## Deployment Problems

### Deployment Stuck in "Building" Status

**Diagnosis:**
```bash
# Check deployment status
curl -X GET https://api.serveml.com/api/v1/deployments/<deployment-id> \
  -H "Authorization: Bearer <token>"

# Check build logs
serveml logs <deployment-id> --type build
```

**Common Causes:**

1. **Large model file (>250MB)**
   - Solution: Compress model or use model pruning
   ```python
   import pickle
   import gzip
   
   # Compress model
   with gzip.open('model.pkl.gz', 'wb') as f:
       pickle.dump(model, f, protocol=4)
   ```

2. **Invalid requirements.txt**
   - Check for typos in package names
   - Verify all packages exist on PyPI
   - Test locally:
   ```bash
   python -m venv test_env
   source test_env/bin/activate
   pip install -r requirements.txt
   ```

3. **Incompatible dependencies**
   ```bash
   # Use pip-tools to resolve conflicts
   pip install pip-tools
   pip-compile requirements.in
   ```

### Deployment Fails Immediately

**Error Types:**

1. **"Model validation failed"**
   ```python
   # Test model loading locally
   import pickle
   
   try:
       with open('model.pkl', 'rb') as f:
           model = pickle.load(f)
       print(f"Model type: {type(model)}")
       print(f"Model attributes: {dir(model)}")
   except Exception as e:
       print(f"Error loading model: {e}")
   ```

2. **"Unsupported framework"**
   - Ensure model is saved in correct format:
   ```python
   # Scikit-learn
   import joblib
   joblib.dump(model, 'model.pkl')
   
   # PyTorch
   torch.save(model, 'model.pt')
   
   # TensorFlow
   model.save('model.h5')
   ```

3. **"File too large"**
   ```bash
   # Check file sizes
   ls -lh model.pkl requirements.txt
   
   # Total should be < 250MB
   ```

### Container Build Errors

**Debugging Steps:**

1. **Check Dockerfile syntax:**
```dockerfile
# ServeML base Dockerfile
FROM public.ecr.aws/lambda/python:3.9

# Common issues:
# - Wrong Python version
# - Missing system dependencies
# - Incorrect file paths
```

2. **Test locally with Docker:**
```bash
# Build locally
docker build -t test-model .

# Run locally
docker run -p 9000:8080 test-model

# Test endpoint
curl -X POST http://localhost:9000/2015-03-31/functions/function/invocations \
  -d '{"data": [1, 2, 3, 4]}'
```

## Prediction Errors

### 500 Internal Server Error

**Diagnosis Flow:**

```mermaid
graph TD
    A[500 Error] --> B{Check Logs}
    B --> C[Model Loading Error]
    B --> D[Input Shape Mismatch]
    B --> E[Memory Error]
    B --> F[Timeout]
    
    C --> G[Verify Model File]
    D --> H[Check Input Format]
    E --> I[Increase Memory]
    F --> J[Optimize Model]
```

**Common Solutions:**

1. **Input shape mismatch:**
```python
# Debug input shape
def diagnose_input(model, sample_input):
    print(f"Input shape: {np.array(sample_input).shape}")
    print(f"Input dtype: {np.array(sample_input).dtype}")
    
    # For sklearn
    if hasattr(model, 'n_features_in_'):
        print(f"Model expects: {model.n_features_in_} features")
    
    # For neural networks
    if hasattr(model, 'input_shape'):
        print(f"Model input shape: {model.input_shape}")
```

2. **Memory errors:**
```python
# Monitor memory usage
import psutil
import os

def check_memory():
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    print(f"Memory usage: {mem_info.rss / 1024 / 1024:.2f} MB")
```

3. **Timeout errors:**
```python
# Profile prediction time
import time

def profile_prediction(model, input_data):
    times = []
    for _ in range(10):
        start = time.time()
        model.predict(input_data)
        times.append(time.time() - start)
    
    print(f"Avg time: {np.mean(times):.3f}s")
    print(f"Max time: {np.max(times):.3f}s")
```

### Incorrect Predictions

**Debugging Steps:**

1. **Verify model version:**
```python
# Add version info to model
model._version = "v1.2.3"
model._training_date = "2024-01-15"
model._metrics = {"accuracy": 0.95, "f1": 0.93}

# Check in production
print(f"Model version: {model._version}")
```

2. **Input preprocessing:**
```python
# Common preprocessing issues
def preprocess_input(raw_input):
    # Ensure correct dtype
    data = np.array(raw_input, dtype=np.float32)
    
    # Check for NaN/Inf
    if np.any(np.isnan(data)) or np.any(np.isinf(data)):
        raise ValueError("Input contains NaN or Inf")
    
    # Apply same scaling as training
    # data = scaler.transform(data)
    
    return data
```

3. **Feature engineering mismatch:**
```python
# Save preprocessing pipeline with model
import pickle

preprocessing_pipeline = {
    'scaler': scaler,
    'encoder': encoder,
    'feature_names': feature_names
}

with open('preprocessing.pkl', 'wb') as f:
    pickle.dump(preprocessing_pipeline, f)
```

## Performance Issues

### High Latency

**Diagnosis:**

```bash
# Measure end-to-end latency
time curl -X POST https://api.serveml.com/api/v1/predict/<id> \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"data": [1, 2, 3, 4]}'

# Check cold start impact
for i in {1..10}; do
  time curl -X POST ... > /dev/null 2>&1
  sleep 60  # Wait for container to cool down
done
```

**Optimization Strategies:**

1. **Reduce model size:**
```python
# Model compression for sklearn
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier

# Convert RF to single tree (lossy)
rf_model = RandomForestClassifier(n_estimators=100)
# ... train model ...

# Extract decision path
tree_model = DecisionTreeClassifier(max_depth=10)
tree_model.fit(X, rf_model.predict(X))
```

2. **Enable provisioned concurrency:**
```python
# Request via API
{
  "deployment_id": "dep-123",
  "provisioned_concurrency": 5
}
```

3. **Optimize dependencies:**
```txt
# Use lighter alternatives
# Instead of: pandas==2.0.3 (50MB)
# Use: numpy==1.24.3 (20MB) + custom code

# Instead of: tensorflow==2.13.0 (500MB+)  
# Use: tensorflow-lite==2.13.0 (5MB)
```

### Cold Start Issues

**Measurement:**

```python
import time
import requests
import matplotlib.pyplot as plt

def measure_cold_starts(url, token, num_tests=20):
    latencies = []
    
    for i in range(num_tests):
        # Make request
        start = time.time()
        response = requests.post(url, 
            headers={"Authorization": f"Bearer {token}"},
            json={"data": [1, 2, 3, 4]}
        )
        latency = time.time() - start
        latencies.append(latency)
        
        # Wait for container to go cold
        if i < num_tests - 1:
            time.sleep(300)  # 5 minutes
    
    # Plot results
    plt.figure(figsize=(10, 6))
    plt.plot(latencies, 'bo-')
    plt.axhline(y=np.mean(latencies), color='r', linestyle='--', 
                label=f'Mean: {np.mean(latencies):.2f}s')
    plt.xlabel('Request Number')
    plt.ylabel('Latency (seconds)')
    plt.title('Cold Start Latency Analysis')
    plt.legend()
    plt.grid(True)
    plt.savefig('cold_starts.png')
```

**Mitigation:**

1. **Keep containers warm:**
```python
# Scheduled warmer function
import boto3
from datetime import datetime

def lambda_handler(event, context):
    lambda_client = boto3.client('lambda')
    
    # List all model serving functions
    functions = lambda_client.list_functions(
        FunctionVersion='ALL',
        MaxItems=1000
    )
    
    # Invoke each function
    for function in functions['Functions']:
        if function['FunctionName'].startswith('serveml-model-'):
            lambda_client.invoke(
                FunctionName=function['FunctionName'],
                InvocationType='RequestResponse',
                Payload='{"warmup": true}'
            )
    
    return {
        'statusCode': 200,
        'body': f'Warmed {len(functions)} functions'
    }
```

## Infrastructure Problems

### Lambda Function Errors

**CloudWatch Insights Query:**

```sql
fields @timestamp, @message
| filter @type = "REPORT"
| stats max(@duration) as max_duration,
        avg(@duration) as avg_duration,
        min(@duration) as min_duration,
        count(*) as invocations
by bin(5m)
```

**Common Lambda Issues:**

1. **Out of Memory:**
```python
# Monitor memory in Lambda
import json

def lambda_handler(event, context):
    # Log memory usage
    print(json.dumps({
        'memory_limit': context.memory_limit_in_mb,
        'memory_used': int(context.memory_limit_in_mb - 
                           (psutil.virtual_memory().available / 1024 / 1024))
    }))
```

2. **Timeout:**
```python
# Add progress logging
import time

def long_running_task(context):
    start_time = time.time()
    
    for i in range(100):
        # Check remaining time
        elapsed = time.time() - start_time
        remaining = context.get_remaining_time_in_millis() / 1000
        
        if remaining < 10:  # Less than 10 seconds
            print(f"Approaching timeout, completed {i}/100")
            break
        
        # Do work...
        process_batch(i)
```

### DynamoDB Throttling

**Detection:**

```python
import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('serveml-deployments')

try:
    response = table.get_item(Key={'id': 'test'})
except ClientError as e:
    if e.response['Error']['Code'] == 'ProvisionedThroughputExceededException':
        print("DynamoDB throttled!")
        print(f"Retry after: {e.response['ResponseMetadata']['RetryAttempts']}")
```

**Solutions:**

1. **Enable auto-scaling:**
```bash
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb \
  --resource-id "table/serveml-deployments" \
  --scalable-dimension "dynamodb:table:ReadCapacityUnits" \
  --min-capacity 5 \
  --max-capacity 40000
```

2. **Implement exponential backoff:**
```python
from boto3.dynamodb.types import TypeDeserializer
import time

def dynamodb_retry(operation, max_retries=3):
    for attempt in range(max_retries):
        try:
            return operation()
        except ClientError as e:
            if e.response['Error']['Code'] != 'ProvisionedThroughputExceededException':
                raise
            
            # Exponential backoff
            wait_time = (2 ** attempt) * 0.1
            time.sleep(wait_time)
    
    raise Exception("Max retries exceeded")
```

### S3 Access Issues

**Diagnosis:**

```bash
# Test S3 access
aws s3 ls s3://serveml-models/ --recursive

# Check bucket policy
aws s3api get-bucket-policy --bucket serveml-models

# Verify CORS
aws s3api get-bucket-cors --bucket serveml-models
```

**Common Issues:**

1. **CORS errors:**
```json
{
  "CORSRules": [
    {
      "AllowedHeaders": ["*"],
      "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
      "AllowedOrigins": ["https://serveml.com"],
      "ExposeHeaders": ["ETag"],
      "MaxAgeSeconds": 3000
    }
  ]
}
```

2. **Presigned URL expiration:**
```python
# Generate longer-lived URLs
s3_client = boto3.client('s3')
url = s3_client.generate_presigned_url(
    'put_object',
    Params={'Bucket': 'serveml-models', 'Key': 'model.pkl'},
    ExpiresIn=7200  # 2 hours instead of default 1 hour
)
```

## Security Issues

### SSL/TLS Errors

**Common Problems:**

1. **Certificate verification failed:**
```python
# Temporary workaround (NOT for production)
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

# Proper solution - update certificates
pip install --upgrade certifi
```

2. **Mixed content warnings:**
```javascript
// Ensure all resources use HTTPS
const apiUrl = window.location.protocol === 'https:' 
  ? 'https://api.serveml.com' 
  : 'http://localhost:8000';
```

### IAM Permission Errors

**Debugging IAM:**

```bash
# Simulate policy evaluation
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::123456789012:role/serveml-api \
  --action-names s3:GetObject \
  --resource-arns arn:aws:s3:::serveml-models/*

# Decode access denied messages
aws sts decode-authorization-message \
  --encoded-message <encoded-message>
```

## Debugging Tools

### Local Testing Environment

```bash
# docker-compose.yml for local testing
version: '3.8'
services:
  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - ENV=development
      - AWS_ENDPOINT_URL=http://localstack:4566
    volumes:
      - ./backend:/app
    command: uvicorn app:app --reload --host 0.0.0.0

  localstack:
    image: localstack/localstack
    ports:
      - "4566:4566"
    environment:
      - SERVICES=s3,dynamodb,lambda
      - DEBUG=1
    volumes:
      - ./localstack:/docker-entrypoint-initaws.d
```

### Log Analysis

```python
# Parse CloudWatch logs
import json
import gzip
import base64

def parse_cloudwatch_logs(event):
    """Extract and parse CloudWatch log data"""
    cw_logs = event['awslogs']['data']
    compressed_payload = base64.b64decode(cw_logs)
    uncompressed_payload = gzip.decompress(compressed_payload)
    log_data = json.loads(uncompressed_payload)
    
    for log_event in log_data['logEvents']:
        message = log_event['message']
        timestamp = log_event['timestamp']
        
        # Parse structured logs
        try:
            log_json = json.loads(message)
            if log_json.get('level') == 'ERROR':
                analyze_error(log_json)
        except:
            # Handle unstructured logs
            if 'ERROR' in message:
                print(f"Error at {timestamp}: {message}")
```

### Performance Profiling

```python
# Profile model prediction
import cProfile
import pstats
from io import StringIO

def profile_model(model, test_data):
    profiler = cProfile.Profile()
    
    # Profile prediction
    profiler.enable()
    for _ in range(100):
        model.predict(test_data)
    profiler.disable()
    
    # Get results
    s = StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
    ps.print_stats(20)  # Top 20 functions
    
    print(s.getvalue())
```

## Support Escalation

### Level 1: Self-Service
- Check this troubleshooting guide
- Search [community forum](https://community.serveml.com)
- Review [API documentation](https://docs.serveml.com)

### Level 2: Community Support
- Post on [Stack Overflow](https://stackoverflow.com/questions/tagged/serveml)
- Join [Discord server](https://discord.gg/serveml)
- GitHub [Discussions](https://github.com/serveml/serveml/discussions)

### Level 3: Technical Support
- Email: support@serveml.com
- Include:
  - Deployment ID
  - Error messages
  - Steps to reproduce
  - Debug logs

### Level 4: Enterprise Support
- 24/7 phone support: +1-xxx-xxx-xxxx
- Dedicated Slack channel
- SLA: 1-hour response time

## Quick Reference

### Common Commands

```bash
# Check deployment status
serveml status <deployment-id>

# View logs
serveml logs <deployment-id> --tail 100

# Test locally
serveml test --model model.pkl --input test.json

# Debug mode
export SERVEML_DEBUG=true
serveml deploy --verbose

# Force rebuild
serveml deploy --force --no-cache
```

### Environment Variables

```bash
# API configuration
SERVEML_API_URL=https://api.serveml.com
SERVEML_API_KEY=your-api-key

# Debug settings
SERVEML_DEBUG=true
SERVEML_LOG_LEVEL=DEBUG

# Performance tuning
SERVEML_TIMEOUT=60
SERVEML_MAX_RETRIES=5
```

### Health Check Endpoints

```bash
# API health
curl https://api.serveml.com/health

# Specific deployment health
curl https://api.serveml.com/api/v1/deployments/<id>/health

# Model serving health
curl https://api.serveml.com/api/v1/predict/<id>/health
```