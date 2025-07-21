# ServeML User Guide

Welcome to ServeML! This guide will help you deploy your machine learning models to production in minutes.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Preparing Your Model](#preparing-your-model)
3. [Deploying Models](#deploying-models)
4. [Testing Deployments](#testing-deployments)
5. [Managing Deployments](#managing-deployments)
6. [Monitoring & Metrics](#monitoring--metrics)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

## Getting Started

### 1. Create an Account

Visit [ServeML.com](https://serveml.com) and sign up:

```bash
# Using the CLI
serveml auth register --email your@email.com --username yourusername

# Or using the API
curl -X POST https://api.serveml.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your@email.com",
    "username": "yourusername",
    "password": "your-secure-password"
  }'
```

### 2. Install the CLI (Optional)

```bash
# Using pip
pip install serveml-cli

# Using homebrew (macOS)
brew install serveml

# Verify installation
serveml --version
```

### 3. Login

```bash
# CLI
serveml auth login

# API
curl -X POST https://api.serveml.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your@email.com",
    "password": "your-password"
  }'
```

## Preparing Your Model

### Supported Frameworks

ServeML supports the following ML frameworks:

- **scikit-learn** (0.24+)
- **PyTorch** (1.9+)
- **TensorFlow/Keras** (2.6+)
- **XGBoost** (1.4+)
- **LightGBM** (3.0+)

### Model Requirements

#### 1. Scikit-learn Models

```python
# train_model.py
import pickle
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import load_iris

# Train your model
X, y = load_iris(return_X_y=True)
model = RandomForestClassifier()
model.fit(X, y)

# Save as pickle file
with open('model.pkl', 'wb') as f:
    pickle.dump(model, f)

# Alternative: Use joblib
import joblib
joblib.dump(model, 'model.pkl')
```

#### 2. PyTorch Models

```python
# train_model.py
import torch
import torch.nn as nn

class MyModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.linear = nn.Linear(10, 3)
    
    def forward(self, x):
        return self.linear(x)

# Train your model
model = MyModel()
# ... training code ...

# Save entire model
torch.save(model, 'model.pt')

# Or save just state dict
torch.save(model.state_dict(), 'model_state.pth')
```

#### 3. TensorFlow/Keras Models

```python
# train_model.py
import tensorflow as tf

# Create and train model
model = tf.keras.Sequential([
    tf.keras.layers.Dense(64, activation='relu', input_shape=(10,)),
    tf.keras.layers.Dense(3, activation='softmax')
])
model.compile(optimizer='adam', loss='sparse_categorical_crossentropy')
# ... training code ...

# Save in SavedModel format
model.save('my_model')

# Or save as H5
model.save('model.h5')
```

### Requirements File

Create a `requirements.txt` file listing all dependencies:

```txt
# requirements.txt
scikit-learn==1.3.0
numpy==1.24.3
pandas==2.0.3
```

**Important**: 
- Pin exact versions for reproducibility
- Include only necessary packages
- Keep total size under 250MB

## Deploying Models

### Using the Web Interface

1. Go to [ServeML Dashboard](https://serveml.com/dashboard)
2. Click "New Deployment"
3. Upload your model file and requirements.txt
4. Choose deployment settings
5. Click "Deploy"

### Using the CLI

```bash
# Basic deployment
serveml deploy --model model.pkl --requirements requirements.txt --name "iris-classifier"

# With custom settings
serveml deploy \
  --model model.pkl \
  --requirements requirements.txt \
  --name "iris-classifier" \
  --memory 2048 \
  --timeout 60
```

### Using the API

```python
import requests

# Get auth token
login_response = requests.post(
    "https://api.serveml.com/api/v1/auth/login",
    json={"email": "your@email.com", "password": "your-password"}
)
token = login_response.json()["access_token"]

# Deploy model
with open('model.pkl', 'rb') as model_file, \
     open('requirements.txt', 'rb') as req_file:
    
    files = {
        'model_file': ('model.pkl', model_file, 'application/octet-stream'),
        'requirements_file': ('requirements.txt', req_file, 'text/plain')
    }
    
    response = requests.post(
        "https://api.serveml.com/api/v1/deploy",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
        data={"name": "iris-classifier"}
    )
    
    deployment = response.json()
    print(f"Deployment ID: {deployment['id']}")
```

### Deployment Options

| Option | Description | Default |
|--------|-------------|---------|
| `name` | Deployment name | Auto-generated |
| `memory` | Memory allocation (MB) | 1024 |
| `timeout` | Request timeout (seconds) | 30 |
| `min_instances` | Minimum instances | 0 |
| `max_instances` | Maximum instances | 10 |

## Testing Deployments

### 1. Check Deployment Status

```bash
# CLI
serveml status <deployment-id>

# API
curl -X GET https://api.serveml.com/api/v1/deployments/<deployment-id> \
  -H "Authorization: Bearer <token>"
```

### 2. Test Predictions

```python
# Python example
import requests

# Single prediction
response = requests.post(
    "https://api.serveml.com/api/v1/predict/<deployment-id>",
    json={"data": [5.1, 3.5, 1.4, 0.2]},
    headers={"Authorization": f"Bearer {token}"}
)
prediction = response.json()
print(f"Prediction: {prediction['result']}")

# Batch prediction
response = requests.post(
    "https://api.serveml.com/api/v1/predict/<deployment-id>",
    json={
        "data": [
            [5.1, 3.5, 1.4, 0.2],
            [6.2, 3.4, 5.4, 2.3],
            [4.9, 3.0, 1.4, 0.2]
        ]
    },
    headers={"Authorization": f"Bearer {token}"}
)
predictions = response.json()
print(f"Predictions: {predictions['results']}")
```

### 3. Test Endpoint URL

Once deployed, your model is available at:
```
https://api.serveml.com/api/v1/predict/<deployment-id>
```

### Input Format

```json
{
  "data": [1.0, 2.0, 3.0, 4.0]  // Single prediction
}

// Or for batch predictions
{
  "data": [
    [1.0, 2.0, 3.0, 4.0],
    [5.0, 6.0, 7.0, 8.0]
  ]
}
```

### Output Format

```json
{
  "prediction": 0,  // For classification
  "probabilities": [0.8, 0.15, 0.05],  // If available
  "model_version": "v1",
  "response_time_ms": 45
}
```

## Managing Deployments

### List All Deployments

```bash
# CLI
serveml list

# API
curl -X GET https://api.serveml.com/api/v1/deployments \
  -H "Authorization: Bearer <token>"
```

### Update Deployment

```bash
# Update configuration
serveml update <deployment-id> --memory 2048 --timeout 60

# Update model version
serveml update <deployment-id> --model new_model.pkl
```

### Delete Deployment

```bash
# CLI
serveml delete <deployment-id>

# API
curl -X DELETE https://api.serveml.com/api/v1/deployments/<deployment-id> \
  -H "Authorization: Bearer <token>"
```

### Deployment Versions

ServeML automatically versions your deployments:

```bash
# List versions
serveml versions <deployment-id>

# Rollback to previous version
serveml rollback <deployment-id> --version v2

# Promote version
serveml promote <deployment-id> --version v3 --to production
```

## Monitoring & Metrics

### View Metrics

```bash
# CLI
serveml metrics <deployment-id> --hours 24

# API
curl -X GET "https://api.serveml.com/api/v1/metrics/<deployment-id>?hours=24" \
  -H "Authorization: Bearer <token>"
```

### Available Metrics

- **Request Count**: Total predictions made
- **Average Latency**: Response time in milliseconds
- **Error Rate**: Percentage of failed requests
- **Cold Starts**: Number of cold start invocations
- **Cost**: Estimated cost for the period

### Setting Up Alerts

```python
# Create alert
alert = {
    "deployment_id": "dep-123",
    "metric": "error_rate",
    "threshold": 0.01,  # 1%
    "comparison": "greater_than",
    "notification_email": "alerts@yourcompany.com"
}

response = requests.post(
    "https://api.serveml.com/api/v1/alerts",
    json=alert,
    headers={"Authorization": f"Bearer {token}"}
)
```

## Best Practices

### 1. Model Optimization

- **Reduce Model Size**: Use model compression techniques
- **Optimize Dependencies**: Include only necessary packages
- **Use Efficient Formats**: Prefer joblib over pickle for scikit-learn

### 2. Performance Tips

```python
# Batch predictions for better performance
predictions = model.predict([
    [5.1, 3.5, 1.4, 0.2],
    [6.2, 3.4, 5.4, 2.3],
    # ... more samples
])

# Pre-warm your model
response = requests.post(
    "https://api.serveml.com/api/v1/warmup/<deployment-id>",
    headers={"Authorization": f"Bearer {token}"}
)
```

### 3. Security

- Use environment variables for sensitive data
- Rotate API keys regularly
- Enable IP whitelisting for production

### 4. Cost Optimization

- Set appropriate memory limits
- Use auto-scaling wisely
- Monitor and optimize cold starts
- Delete unused deployments

## Troubleshooting

### Common Issues

#### 1. Deployment Fails

**Symptom**: Deployment status shows "failed"

**Solutions**:
- Check requirements.txt for typos
- Ensure all dependencies are available on PyPI
- Verify model file is not corrupted
- Check total size is under 250MB

#### 2. Predictions Return Errors

**Symptom**: 500 error when making predictions

**Solutions**:
- Verify input format matches training data
- Check model expects correct input shape
- Review deployment logs for errors

#### 3. High Latency

**Symptom**: Predictions take >1 second

**Solutions**:
- Reduce model complexity
- Enable provisioned concurrency
- Use batch predictions
- Optimize dependencies

### Debug Commands

```bash
# View deployment logs
serveml logs <deployment-id> --tail 100

# Check deployment details
serveml describe <deployment-id>

# Test locally before deploying
serveml test --model model.pkl --requirements requirements.txt --input sample.json
```

### Getting Help

1. **Documentation**: [docs.serveml.com](https://docs.serveml.com)
2. **Community Forum**: [community.serveml.com](https://community.serveml.com)
3. **Support Email**: support@serveml.com
4. **GitHub Issues**: [github.com/serveml/serveml](https://github.com/serveml/serveml)

## Examples

### Complete Example: Iris Classifier

```python
# 1. Train model
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import load_iris
import joblib

X, y = load_iris(return_X_y=True)
model = RandomForestClassifier(n_estimators=100)
model.fit(X, y)
joblib.dump(model, 'iris_model.pkl')

# 2. Create requirements.txt
with open('requirements.txt', 'w') as f:
    f.write('scikit-learn==1.3.0\nnumpy==1.24.3\njoblib==1.3.0')

# 3. Deploy
import requests

# Login
auth = requests.post(
    "https://api.serveml.com/api/v1/auth/login",
    json={"email": "user@example.com", "password": "password"}
)
token = auth.json()["access_token"]

# Deploy
with open('iris_model.pkl', 'rb') as m, open('requirements.txt', 'rb') as r:
    files = {
        'model_file': ('iris_model.pkl', m, 'application/octet-stream'),
        'requirements_file': ('requirements.txt', r, 'text/plain')
    }
    deploy_response = requests.post(
        "https://api.serveml.com/api/v1/deploy",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
        data={"name": "iris-classifier"}
    )

deployment_id = deploy_response.json()["id"]

# 4. Test prediction
test_response = requests.post(
    f"https://api.serveml.com/api/v1/predict/{deployment_id}",
    json={"data": [5.1, 3.5, 1.4, 0.2]},
    headers={"Authorization": f"Bearer {token}"}
)
print(f"Prediction: {test_response.json()}")
```

## FAQ

**Q: How much does ServeML cost?**
A: Pay only for what you use. See [pricing](https://serveml.com/pricing) for details.

**Q: What regions are supported?**
A: Currently US East (Virginia), with more regions coming soon.

**Q: Can I use custom Docker images?**
A: Not yet, but this feature is on our roadmap.

**Q: Is there a free tier?**
A: Yes! First 1000 predictions per month are free.

**Q: How do I handle model versioning?**
A: ServeML automatically versions each deployment. Use the CLI or API to manage versions.

---

Ready to deploy? [Sign up now](https://serveml.com/signup) and get your model live in minutes!