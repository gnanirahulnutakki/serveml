# ServeML MVP Implementation Guide

## Quick Start: What We're Building First

For the MVP, we're focusing on the absolute minimum to deploy a scikit-learn model:

1. **Simple web form** to upload model.pkl and requirements.txt
2. **Basic API** that receives files and triggers deployment
3. **Automated pipeline** that packages and deploys to Lambda
4. **Working endpoint** that serves predictions

No authentication, no fancy UI, no complex features - just the core functionality.

## Step-by-Step Implementation Plan

### Step 1: Create Basic Project Structure

```bash
serveml/
├── backend/
│   ├── app.py              # Simple FastAPI app
│   ├── requirements.txt    # Python dependencies
│   └── templates/
│       ├── wrapper.py      # Model serving template
│       └── Dockerfile      # Lambda container template
├── frontend/
│   ├── index.html          # Simple upload form
│   ├── app.js              # Basic JavaScript
│   └── style.css           # Minimal styling
├── .github/
│   └── workflows/
│       └── deploy.yml      # GitHub Actions workflow
└── docker-compose.yml      # Local development setup
```

### Step 2: Backend API (Minimal FastAPI)

```python
# backend/app.py
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import boto3
import uuid
import os
from typing import Optional

app = FastAPI(title="ServeML MVP")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-memory storage for MVP (replace with DynamoDB later)
deployments = {}

class DeploymentResponse(BaseModel):
    id: str
    status: str
    endpoint_url: Optional[str] = None

@app.post("/deploy", response_model=DeploymentResponse)
async def deploy_model(
    model_file: UploadFile = File(...),
    requirements_file: UploadFile = File(...)
):
    """Deploy a model - MVP version"""
    
    # Generate unique deployment ID
    deployment_id = str(uuid.uuid4())
    
    # Save files to S3 (using local filesystem for MVP)
    os.makedirs(f"uploads/{deployment_id}", exist_ok=True)
    
    # Save model file
    with open(f"uploads/{deployment_id}/model.pkl", "wb") as f:
        content = await model_file.read()
        f.write(content)
    
    # Save requirements
    with open(f"uploads/{deployment_id}/requirements.txt", "wb") as f:
        content = await requirements_file.read()
        f.write(content)
    
    # Store deployment info
    deployments[deployment_id] = {
        "status": "deploying",
        "endpoint_url": None
    }
    
    # TODO: Trigger GitHub Actions workflow
    # For MVP, we'll manually trigger or use webhooks
    
    return DeploymentResponse(
        id=deployment_id,
        status="deploying"
    )

@app.get("/deployments/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(deployment_id: str):
    """Get deployment status"""
    if deployment_id not in deployments:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    deployment = deployments[deployment_id]
    return DeploymentResponse(
        id=deployment_id,
        status=deployment["status"],
        endpoint_url=deployment["endpoint_url"]
    )

@app.get("/health")
async def health():
    return {"status": "healthy"}
```

### Step 3: Simple Frontend

```html
<!-- frontend/index.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ServeML - Deploy Your Model</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <h1>ServeML</h1>
        <p>Deploy your ML model in one click</p>
        
        <div id="upload-form">
            <h2>Upload Your Model</h2>
            <form id="deploy-form">
                <div class="form-group">
                    <label for="model-file">Model File (.pkl)</label>
                    <input type="file" id="model-file" accept=".pkl" required>
                </div>
                
                <div class="form-group">
                    <label for="requirements-file">Requirements.txt</label>
                    <input type="file" id="requirements-file" accept=".txt" required>
                </div>
                
                <button type="submit">Deploy Model</button>
            </form>
        </div>
        
        <div id="deployment-status" style="display: none;">
            <h2>Deployment Status</h2>
            <p>Deployment ID: <span id="deployment-id"></span></p>
            <p>Status: <span id="status"></span></p>
            <p>Endpoint: <span id="endpoint"></span></p>
        </div>
    </div>
    
    <script src="app.js"></script>
</body>
</html>
```

```javascript
// frontend/app.js
const API_URL = 'http://localhost:8000';

document.getElementById('deploy-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const modelFile = document.getElementById('model-file').files[0];
    const requirementsFile = document.getElementById('requirements-file').files[0];
    
    if (!modelFile || !requirementsFile) {
        alert('Please select both files');
        return;
    }
    
    const formData = new FormData();
    formData.append('model_file', modelFile);
    formData.append('requirements_file', requirementsFile);
    
    try {
        const response = await fetch(`${API_URL}/deploy`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        // Show deployment status
        document.getElementById('upload-form').style.display = 'none';
        document.getElementById('deployment-status').style.display = 'block';
        document.getElementById('deployment-id').textContent = data.id;
        document.getElementById('status').textContent = data.status;
        
        // Poll for status updates
        pollDeploymentStatus(data.id);
        
    } catch (error) {
        alert('Deployment failed: ' + error.message);
    }
});

async function pollDeploymentStatus(deploymentId) {
    const interval = setInterval(async () => {
        try {
            const response = await fetch(`${API_URL}/deployments/${deploymentId}`);
            const data = await response.json();
            
            document.getElementById('status').textContent = data.status;
            
            if (data.endpoint_url) {
                document.getElementById('endpoint').textContent = data.endpoint_url;
                clearInterval(interval);
            }
        } catch (error) {
            console.error('Error polling status:', error);
        }
    }, 5000); // Poll every 5 seconds
}
```

### Step 4: Model Wrapper Template

```python
# backend/templates/wrapper.py
"""
Generic model serving wrapper for Lambda
This gets customized for each deployment
"""
import os
import pickle
import json

def load_model():
    """Load the pickled model"""
    model_path = os.environ.get('MODEL_PATH', '/opt/ml/model.pkl')
    with open(model_path, 'rb') as f:
        return pickle.load(f)

# Load model at cold start
model = load_model()

def lambda_handler(event, context):
    """Lambda handler for predictions"""
    try:
        # Parse input
        body = json.loads(event.get('body', '{}'))
        data = body.get('data', [])
        
        # Make prediction
        prediction = model.predict([data])
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'prediction': prediction.tolist()[0],
                'model_type': type(model).__name__
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }
```

### Step 5: Docker Template for Lambda

```dockerfile
# backend/templates/Dockerfile
FROM public.ecr.aws/lambda/python:3.11

# Copy requirements and install
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy model and handler
COPY model.pkl /opt/ml/model.pkl
COPY handler.py ${LAMBDA_TASK_ROOT}

# Set handler
CMD ["handler.lambda_handler"]
```

### Step 6: Local Development Setup

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - ./uploads:/uploads
    command: uvicorn app:app --host 0.0.0.0 --reload
    environment:
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_REGION=us-east-1

  frontend:
    image: nginx:alpine
    ports:
      - "3000:80"
    volumes:
      - ./frontend:/usr/share/nginx/html
```

### Step 7: Minimal GitHub Actions Workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy Model
on:
  workflow_dispatch:
    inputs:
      deployment_id:
        description: 'Deployment ID'
        required: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Create deployment package
      run: |
        # Copy templates
        mkdir -p build
        cp backend/templates/wrapper.py build/handler.py
        cp backend/templates/Dockerfile build/
        
        # Copy model files (from S3 in production)
        cp uploads/${{ inputs.deployment_id }}/model.pkl build/
        cp uploads/${{ inputs.deployment_id }}/requirements.txt build/
    
    - name: Build and test locally
      run: |
        cd build
        docker build -t serveml-model:${{ inputs.deployment_id }} .
        
    # TODO: Add ECR push and Lambda deployment
    # For MVP, we'll test locally first
```

## Testing the MVP Locally

### 1. Start the Backend
```bash
cd backend
pip install fastapi uvicorn boto3 python-multipart
uvicorn app:app --reload
```

### 2. Serve the Frontend
```bash
cd frontend
python -m http.server 3000
```

### 3. Create a Test Model
```python
# create_test_model.py
import pickle
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier

# Train a simple model
X, y = load_iris(return_X_y=True)
model = RandomForestClassifier(n_estimators=10)
model.fit(X, y)

# Save model
with open('model.pkl', 'wb') as f:
    pickle.dump(model, f)

# Create requirements.txt
with open('requirements.txt', 'w') as f:
    f.write('scikit-learn==1.3.0\nnumpy==1.24.3\n')
```

### 4. Test the Deployment
1. Open http://localhost:3000
2. Upload model.pkl and requirements.txt
3. Check deployment status
4. Test the endpoint (once deployed)

## MVP Limitations & Next Steps

### Current Limitations
- No authentication
- No real AWS integration
- Manual deployment triggering
- No persistence (in-memory storage)
- No error handling
- No monitoring

### Immediate Next Steps
1. **AWS Integration**
   - Set up S3 bucket for uploads
   - Create ECR repository
   - Configure Lambda and API Gateway
   
2. **Automation**
   - S3 event triggers
   - Automated GitHub Actions
   - DynamoDB for persistence

3. **Production Readiness**
   - Error handling
   - Input validation
   - Basic authentication
   - HTTPS setup

## Development Tips

1. **Start Simple**: Get the local version working first
2. **Test with Real Models**: Use actual scikit-learn models
3. **Incremental AWS**: Add AWS services one at a time
4. **Focus on Flow**: Ensure the entire flow works end-to-end
5. **Document Issues**: Keep track of problems for later fixes

This MVP gives us a working prototype that we can demo and iterate on. Once it works locally, we can gradually add AWS services and production features.