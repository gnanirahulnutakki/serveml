# ServeML Architecture Plan

## Overview

This document outlines the complete code architecture for ServeML, a serverless ML model deployment platform. We'll build this system incrementally, starting with a simple MVP and evolving to a production-ready platform.

## 1. System Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                           User Interface                             │
│                         (React + TypeScript)                         │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          Backend API                                 │
│                    (FastAPI + Python 3.11)                          │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   Auth      │  │  Deployments │  │   Metrics    │              │
│  │  Service    │  │   Service    │  │   Service    │              │
│  └─────────────┘  └──────────────┘  └──────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
┌─────────────────────────────┐    ┌─────────────────────────────┐
│         Storage             │    │      Event System           │
│  ┌─────────┐ ┌──────────┐  │    │  ┌──────────┐ ┌──────────┐ │
│  │   S3    │ │ DynamoDB │  │    │  │ S3 Event │ │  Lambda  │ │
│  │ Buckets │ │  Tables  │  │    │  │ Triggers │ │ Triggers │ │
│  └─────────┘ └──────────┘  │    │  └──────────┘ └──────────┘ │
└─────────────────────────────┘    └─────────────────────────────┘
                                                │
                                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Deployment Pipeline                           │
│                       (GitHub Actions)                               │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────────┐ │
│  │   Build    │→ │    Test    │→ │  Package   │→ │    Deploy    │ │
│  │   Docker   │  │   Model    │  │    ECR     │  │   Lambda     │ │
│  └────────────┘  └────────────┘  └────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                                │
                                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Model Serving Layer                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │  Lambda Function │  │  API Gateway     │  │  CloudFront      │ │
│  │  (Container)     │  │  (REST API)      │  │  (CDN/Cache)     │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Model Upload Flow**
   ```
   User → Frontend → Backend API → S3 Presigned URL → Direct Upload
                         ↓
                    DynamoDB (metadata)
                         ↓
                    S3 Event → Lambda Trigger → GitHub Actions
   ```

2. **Model Deployment Flow**
   ```
   GitHub Actions → Docker Build → ECR Push → Lambda Create → API Gateway
                         ↓
                    Update DynamoDB Status
   ```

3. **Model Prediction Flow**
   ```
   Client → API Gateway → Lambda (warm) → Model Prediction → Response
                              ↓
                         CloudWatch Metrics
   ```

## 2. Backend API Design

### FastAPI Application Structure

```python
serveml/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app entry point
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py           # Settings management
│   │   │   ├── security.py         # Auth utilities
│   │   │   └── exceptions.py       # Custom exceptions
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py             # Dependencies
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── endpoints/
│   │   │       │   ├── __init__.py
│   │   │       │   ├── auth.py
│   │   │       │   ├── deployments.py
│   │   │       │   ├── models.py
│   │   │       │   └── metrics.py
│   │   │       └── router.py
│   │   ├── models/                 # Pydantic models
│   │   │   ├── __init__.py
│   │   │   ├── deployment.py
│   │   │   ├── user.py
│   │   │   └── metrics.py
│   │   ├── services/               # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── deployment.py
│   │   │   ├── storage.py
│   │   │   ├── pipeline.py
│   │   │   └── monitoring.py
│   │   ├── db/                     # Database
│   │   │   ├── __init__.py
│   │   │   ├── dynamodb.py
│   │   │   └── models.py
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── aws.py
│   │       └── validators.py
│   ├── templates/                  # Docker/code templates
│   │   ├── dockerfile.j2
│   │   ├── app.py.j2
│   │   └── requirements.txt.j2
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
```

### API Endpoints

```yaml
API Endpoints:
  Authentication:
    POST   /api/v1/auth/register
    POST   /api/v1/auth/login
    POST   /api/v1/auth/refresh
    GET    /api/v1/auth/me

  Deployments:
    GET    /api/v1/deployments              # List user's deployments
    POST   /api/v1/deployments              # Create new deployment
    GET    /api/v1/deployments/{id}         # Get deployment details
    DELETE /api/v1/deployments/{id}         # Delete deployment
    PATCH  /api/v1/deployments/{id}         # Update deployment
    POST   /api/v1/deployments/{id}/rollback # Rollback to previous version

  Models:
    GET    /api/v1/models                   # List deployed models
    GET    /api/v1/models/{id}/versions     # Get model versions
    POST   /api/v1/models/{id}/test        # Test model with sample data

  Metrics:
    GET    /api/v1/metrics/{deployment_id}  # Get deployment metrics
    GET    /api/v1/metrics/usage            # Get usage statistics

  Storage:
    POST   /api/v1/storage/upload-url       # Get presigned upload URL
    POST   /api/v1/storage/validate         # Validate model files
```

### Data Models (Pydantic)

```python
# models/deployment.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum

class DeploymentStatus(str, Enum):
    PENDING = "pending"
    BUILDING = "building"
    DEPLOYING = "deploying"
    ACTIVE = "active"
    FAILED = "failed"
    DELETED = "deleted"

class Framework(str, Enum):
    SKLEARN = "sklearn"
    PYTORCH = "pytorch"
    TENSORFLOW = "tensorflow"
    XGBOOST = "xgboost"
    CUSTOM = "custom"

class DeploymentCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    description: Optional[str] = None
    framework: Framework
    python_version: str = Field(default="3.11")
    environment_vars: Optional[Dict[str, str]] = None

class DeploymentResponse(BaseModel):
    id: str
    user_id: str
    name: str
    status: DeploymentStatus
    framework: Framework
    endpoint_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    version: int = 1
    metrics: Optional[Dict] = None

class ModelFile(BaseModel):
    filename: str
    size: int
    content_type: str
    upload_url: Optional[str] = None
```

## 3. Frontend Architecture

### React Application Structure

```
frontend/
├── src/
│   ├── index.tsx                   # Entry point
│   ├── App.tsx                     # Main app component
│   ├── components/
│   │   ├── common/
│   │   │   ├── Layout.tsx
│   │   │   ├── Header.tsx
│   │   │   ├── Footer.tsx
│   │   │   └── LoadingSpinner.tsx
│   │   ├── auth/
│   │   │   ├── LoginForm.tsx
│   │   │   ├── RegisterForm.tsx
│   │   │   └── ProtectedRoute.tsx
│   │   ├── deployments/
│   │   │   ├── DeploymentList.tsx
│   │   │   ├── DeploymentCard.tsx
│   │   │   ├── DeploymentDetail.tsx
│   │   │   └── NewDeployment.tsx
│   │   ├── models/
│   │   │   ├── ModelUpload.tsx
│   │   │   ├── ModelTest.tsx
│   │   │   └── ModelVersions.tsx
│   │   └── metrics/
│   │       ├── MetricsDashboard.tsx
│   │       ├── UsageChart.tsx
│   │       └── PerformanceMetrics.tsx
│   ├── pages/
│   │   ├── Home.tsx
│   │   ├── Dashboard.tsx
│   │   ├── Deployments.tsx
│   │   ├── Metrics.tsx
│   │   └── Settings.tsx
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useDeployments.ts
│   │   ├── useMetrics.ts
│   │   └── useWebSocket.ts
│   ├── services/
│   │   ├── api.ts
│   │   ├── auth.ts
│   │   ├── deployments.ts
│   │   └── storage.ts
│   ├── store/
│   │   ├── index.ts
│   │   ├── authSlice.ts
│   │   ├── deploymentSlice.ts
│   │   └── notificationSlice.ts
│   ├── types/
│   │   ├── index.ts
│   │   ├── deployment.ts
│   │   └── user.ts
│   └── utils/
│       ├── constants.ts
│       ├── helpers.ts
│       └── validators.ts
```

### Key Frontend Components

```typescript
// types/deployment.ts
export interface Deployment {
  id: string;
  name: string;
  status: DeploymentStatus;
  framework: Framework;
  endpointUrl?: string;
  createdAt: Date;
  updatedAt: Date;
  version: number;
}

// components/deployments/NewDeployment.tsx
interface NewDeploymentProps {
  onSuccess: (deployment: Deployment) => void;
}

const NewDeployment: React.FC<NewDeploymentProps> = ({ onSuccess }) => {
  // Multi-step form:
  // 1. Model details (name, framework)
  // 2. File upload (model file, requirements.txt)
  // 3. Configuration (env vars, python version)
  // 4. Review & Deploy
};
```

## 4. Model Serving Architecture

### Dynamic Docker Container Generation

```python
# templates/app.py.j2
import os
import pickle
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict

app = FastAPI(title="{{ model_name }} API")

# Load model at startup
MODEL_PATH = os.getenv("MODEL_PATH", "/app/model.pkl")
model = None

@app.on_event("startup")
async def load_model():
    global model
    try:
        with open(MODEL_PATH, "rb") as f:
            model = pickle.load(f)
    except Exception as e:
        raise RuntimeError(f"Failed to load model: {str(e)}")

class PredictionRequest(BaseModel):
    data: Dict[str, Any]

class PredictionResponse(BaseModel):
    prediction: Any
    model_version: str = "{{ version }}"
    
@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        prediction = model.predict([list(request.data.values())])
        return PredictionResponse(
            prediction=prediction.tolist()[0],
            model_version="{{ version }}"
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "healthy", "model_loaded": model is not None}
```

### Framework-Specific Optimizations

```python
# services/model_optimizer.py
class ModelOptimizer:
    def optimize_sklearn(self, model_path: str) -> str:
        """Optimize scikit-learn models using joblib"""
        import joblib
        model = joblib.load(model_path)
        # Apply optimizations: pruning, quantization
        optimized_path = model_path.replace('.pkl', '_optimized.pkl')
        joblib.dump(model, optimized_path, compress=3)
        return optimized_path
    
    def optimize_pytorch(self, model_path: str) -> str:
        """Optimize PyTorch models using TorchScript"""
        import torch
        model = torch.load(model_path)
        model.eval()
        # Convert to TorchScript
        scripted = torch.jit.script(model)
        optimized_path = model_path.replace('.pt', '_scripted.pt')
        torch.jit.save(scripted, optimized_path)
        return optimized_path
    
    def optimize_tensorflow(self, model_path: str) -> str:
        """Optimize TensorFlow models using TFLite"""
        import tensorflow as tf
        model = tf.keras.models.load_model(model_path)
        # Convert to TFLite for inference optimization
        converter = tf.lite.TFLiteConverter.from_keras_model(model)
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        return model_path  # Return optimized model
```

## 5. Database Schema

### DynamoDB Tables

```yaml
Tables:
  Deployments:
    PartitionKey: user_id (String)
    SortKey: deployment_id (String)
    Attributes:
      - name (String)
      - status (String)
      - framework (String)
      - endpoint_url (String)
      - created_at (Number)
      - updated_at (Number)
      - version (Number)
      - model_s3_path (String)
      - container_image_uri (String)
      - lambda_function_arn (String)
      - environment_vars (Map)
    GSI:
      - status-index: status (PartitionKey), created_at (SortKey)

  Users:
    PartitionKey: user_id (String)
    Attributes:
      - email (String)
      - username (String)
      - created_at (Number)
      - subscription_tier (String)
      - api_key_hash (String)
    GSI:
      - email-index: email (PartitionKey)

  Metrics:
    PartitionKey: deployment_id (String)
    SortKey: timestamp (Number)
    Attributes:
      - requests_count (Number)
      - errors_count (Number)
      - avg_latency_ms (Number)
      - p99_latency_ms (Number)
      - input_tokens (Number)
      - output_tokens (Number)
```

## 6. Security Architecture

### Authentication & Authorization

```python
# core/security.py
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

class AuthService:
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
    
    def create_access_token(self, user_id: str) -> str:
        expire = datetime.utcnow() + timedelta(hours=24)
        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, credentials: HTTPAuthorizationCredentials) -> str:
        token = credentials.credentials
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload["sub"]
        except JWTError:
            raise HTTPException(status_code=403, detail="Invalid token")
```

### API Rate Limiting

```python
# middleware/rate_limit.py
from fastapi import Request, HTTPException
from typing import Dict, Tuple
import time

class RateLimiter:
    def __init__(self, calls: int = 100, period: int = 3600):
        self.calls = calls
        self.period = period
        self.clients: Dict[str, Tuple[int, float]] = {}
    
    async def __call__(self, request: Request):
        client_id = request.client.host
        now = time.time()
        
        if client_id in self.clients:
            calls, last_reset = self.clients[client_id]
            if now - last_reset > self.period:
                self.clients[client_id] = (1, now)
            elif calls >= self.calls:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            else:
                self.clients[client_id] = (calls + 1, last_reset)
        else:
            self.clients[client_id] = (1, now)
```

## 7. CI/CD Pipeline Design

### GitHub Actions Workflow

```yaml
# .github/workflows/deploy_model.yml
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
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v1
        with:
          role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE }}
          aws-region: us-east-1
      
      - name: Download model artifacts
        run: |
          aws s3 cp s3://serveml-uploads/${{ inputs.deployment_id }}/ ./model/ --recursive
      
      - name: Build container
        run: |
          docker build -t serveml-model:${{ inputs.deployment_id }} .
      
      - name: Push to ECR
        run: |
          aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_URL
          docker tag serveml-model:${{ inputs.deployment_id }} $ECR_URL:${{ inputs.deployment_id }}
          docker push $ECR_URL:${{ inputs.deployment_id }}
      
      - name: Deploy Lambda
        run: |
          aws lambda create-function \
            --function-name serveml-${{ inputs.deployment_id }} \
            --package-type Image \
            --code ImageUri=$ECR_URL:${{ inputs.deployment_id }} \
            --role ${{ secrets.LAMBDA_ROLE }}
```

## 8. Development Workflow

### Local Development Setup

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# Docker Compose for local services
docker-compose up -d
```

### Testing Strategy

```python
# tests/test_deployment.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_deployment():
    response = client.post("/api/v1/deployments", json={
        "name": "test-model",
        "framework": "sklearn",
        "python_version": "3.11"
    })
    assert response.status_code == 201
    assert response.json()["status"] == "pending"

def test_model_prediction():
    response = client.post("/predict", json={
        "data": {"feature1": 1.0, "feature2": 2.0}
    })
    assert response.status_code == 200
    assert "prediction" in response.json()
```

## Next Steps

1. **Set up development environment** with the project structure
2. **Implement core backend services** starting with authentication
3. **Create basic frontend** with upload functionality
4. **Build model serving wrapper** for different frameworks
5. **Test locally** with Docker Compose before AWS integration

This architecture provides a solid foundation that we can implement incrementally, starting with the MVP features and gradually adding more sophisticated capabilities.