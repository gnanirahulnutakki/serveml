# ServeML API Reference

Base URL: `https://api.serveml.com`

## Authentication

ServeML uses JWT tokens for authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your-token>
```

## Endpoints

### Authentication

#### Register User

```http
POST /api/v1/auth/register
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "username": "johndoe",
  "password": "secure-password",
  "full_name": "John Doe"  // optional
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": "user-123",
    "email": "user@example.com",
    "username": "johndoe",
    "created_at": "2024-01-15T10:00:00Z"
  }
}
```

#### Login

```http
POST /api/v1/auth/login
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "secure-password"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

#### Get Current User

```http
GET /api/v1/auth/me
```

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "id": "user-123",
  "email": "user@example.com",
  "username": "johndoe",
  "full_name": "John Doe",
  "created_at": "2024-01-15T10:00:00Z",
  "deployment_count": 5,
  "total_predictions": 15420
}
```

### Deployments

#### Create Deployment

```http
POST /api/v1/deploy
```

**Headers:**
- `Authorization: Bearer <token>`
- `Content-Type: multipart/form-data`

**Form Data:**
- `model_file`: Model file (.pkl, .pt, .h5, .keras, .pth)
- `requirements_file`: Requirements.txt file
- `name`: (optional) Deployment name
- `memory`: (optional) Memory in MB (default: 1024)
- `timeout`: (optional) Timeout in seconds (default: 30)

**Response:**
```json
{
  "id": "dep-abc123",
  "name": "iris-classifier",
  "status": "building",
  "created_at": "2024-01-15T10:30:00Z",
  "model_metadata": {
    "framework": "sklearn",
    "model_type": "RandomForestClassifier",
    "size_mb": 1.2
  }
}
```

#### List Deployments

```http
GET /api/v1/deployments
```

**Headers:**
- `Authorization: Bearer <token>` (optional)

**Query Parameters:**
- `limit`: Number of results (default: 20, max: 100)
- `offset`: Pagination offset (default: 0)
- `status`: Filter by status (active, building, failed, deleted)
- `framework`: Filter by framework (sklearn, pytorch, tensorflow)
- `search`: Search in deployment names

**Response:**
```json
{
  "items": [
    {
      "id": "dep-abc123",
      "name": "iris-classifier",
      "status": "active",
      "created_at": "2024-01-15T10:30:00Z",
      "endpoint_url": "https://api.serveml.com/api/v1/predict/dep-abc123",
      "model_metadata": {
        "framework": "sklearn",
        "model_type": "RandomForestClassifier"
      }
    }
  ],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```

#### Get Deployment

```http
GET /api/v1/deployments/{deployment_id}
```

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "id": "dep-abc123",
  "name": "iris-classifier",
  "status": "active",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:35:00Z",
  "endpoint_url": "https://api.serveml.com/api/v1/predict/dep-abc123",
  "model_metadata": {
    "framework": "sklearn",
    "model_type": "RandomForestClassifier",
    "size_mb": 1.2,
    "input_shape": [4],
    "output_shape": [3]
  },
  "configuration": {
    "memory_mb": 1024,
    "timeout_seconds": 30,
    "min_instances": 0,
    "max_instances": 10
  },
  "metrics_summary": {
    "total_predictions": 1542,
    "avg_latency_ms": 45,
    "error_rate": 0.001
  }
}
```

#### Update Deployment

```http
PATCH /api/v1/deployments/{deployment_id}
```

**Headers:**
- `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "name": "new-name",
  "memory_mb": 2048,
  "timeout_seconds": 60,
  "min_instances": 1,
  "max_instances": 20
}
```

**Response:**
```json
{
  "id": "dep-abc123",
  "name": "new-name",
  "status": "updating",
  "configuration": {
    "memory_mb": 2048,
    "timeout_seconds": 60,
    "min_instances": 1,
    "max_instances": 20
  }
}
```

#### Delete Deployment

```http
DELETE /api/v1/deployments/{deployment_id}
```

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "message": "Deployment deleted successfully",
  "id": "dep-abc123"
}
```

### Predictions

#### Make Prediction

```http
POST /api/v1/predict/{deployment_id}
```

**Headers:**
- `Authorization: Bearer <token>`
- `Content-Type: application/json`

**Request Body (Single Prediction):**
```json
{
  "data": [5.1, 3.5, 1.4, 0.2]
}
```

**Request Body (Batch Prediction):**
```json
{
  "data": [
    [5.1, 3.5, 1.4, 0.2],
    [6.2, 3.4, 5.4, 2.3],
    [4.9, 3.0, 1.4, 0.2]
  ]
}
```

**Response (Single):**
```json
{
  "prediction": 0,
  "probabilities": [0.98, 0.01, 0.01],
  "model_version": "v1",
  "response_time_ms": 42
}
```

**Response (Batch):**
```json
{
  "predictions": [0, 2, 0],
  "probabilities": [
    [0.98, 0.01, 0.01],
    [0.01, 0.02, 0.97],
    [0.95, 0.03, 0.02]
  ],
  "model_version": "v1",
  "response_time_ms": 58,
  "batch_size": 3
}
```

#### Test Model (Internal)

```http
POST /api/v1/test-model
```

**Headers:**
- `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "deployment_id": "dep-abc123",
  "data": {
    "feature1": 5.1,
    "feature2": 3.5,
    "feature3": 1.4,
    "feature4": 0.2
  }
}
```

### Metrics

#### Get Deployment Metrics

```http
GET /api/v1/metrics/{deployment_id}
```

**Headers:**
- `Authorization: Bearer <token>`

**Query Parameters:**
- `hours`: Time range in hours (default: 24, max: 168)
- `resolution`: Data resolution (1m, 5m, 1h, 1d)

**Response:**
```json
{
  "deployment_id": "dep-abc123",
  "period": {
    "start": "2024-01-14T10:00:00Z",
    "end": "2024-01-15T10:00:00Z"
  },
  "metrics": {
    "request_count": 1542,
    "error_count": 2,
    "avg_latency_ms": 45,
    "p95_latency_ms": 120,
    "p99_latency_ms": 250,
    "cold_starts": 15,
    "unique_users": 23
  },
  "time_series": {
    "timestamps": ["2024-01-14T10:00:00Z", "2024-01-14T11:00:00Z", ...],
    "request_counts": [120, 145, ...],
    "avg_latencies": [42, 48, ...]
  },
  "cost_estimate": {
    "total_usd": 0.84,
    "breakdown": {
      "compute": 0.72,
      "storage": 0.10,
      "network": 0.02
    }
  },
  "dashboard_url": "https://serveml.com/dashboard/deployments/dep-abc123/metrics"
}
```

### Versions

#### List Deployment Versions

```http
GET /api/v1/deployments/{deployment_id}/versions
```

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "versions": [
    {
      "version": "v3",
      "created_at": "2024-01-15T10:00:00Z",
      "status": "active",
      "is_current": true,
      "changes": "Updated model with new training data"
    },
    {
      "version": "v2",
      "created_at": "2024-01-14T15:00:00Z",
      "status": "inactive",
      "is_current": false,
      "changes": "Fixed prediction bug"
    }
  ]
}
```

#### Rollback Version

```http
POST /api/v1/deployments/{deployment_id}/rollback
```

**Headers:**
- `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "version": "v2"
}
```

### Health & Status

#### Health Check

```http
GET /
```

**Response:**
```json
{
  "status": "healthy",
  "message": "Welcome to ServeML API",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:00:00Z"
}
```

#### API Status

```http
GET /api/v1/status
```

**Response:**
```json
{
  "api": "operational",
  "deployments": "operational",
  "predictions": "operational",
  "database": "operational",
  "storage": "operational",
  "issues": []
}
```

## Error Responses

All errors follow this format:

```json
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "The provided input is invalid",
    "details": {
      "field": "data",
      "reason": "Expected array of numbers"
    }
  },
  "request_id": "req-xyz789"
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `UNAUTHORIZED` | 401 | Missing or invalid authentication |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `INVALID_INPUT` | 400 | Invalid request data |
| `VALIDATION_ERROR` | 422 | Request validation failed |
| `DEPLOYMENT_FAILED` | 400 | Model deployment failed |
| `PREDICTION_ERROR` | 500 | Error during prediction |
| `RATE_LIMITED` | 429 | Too many requests |
| `SERVICE_ERROR` | 500 | Internal service error |

## Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| Authentication | 10 requests | 1 minute |
| Deployments | 100 requests | 1 hour |
| Predictions | 1000 requests | 1 minute |
| Metrics | 100 requests | 1 hour |

Rate limit headers:
- `X-RateLimit-Limit`: Request limit
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Reset timestamp

## Webhooks

Configure webhooks to receive deployment events:

```http
POST /api/v1/webhooks
```

**Request Body:**
```json
{
  "url": "https://your-app.com/webhook",
  "events": ["deployment.created", "deployment.ready", "deployment.failed"],
  "secret": "webhook-secret"
}
```

### Webhook Events

- `deployment.created`: New deployment initiated
- `deployment.building`: Building Docker image
- `deployment.ready`: Deployment active and ready
- `deployment.failed`: Deployment failed
- `deployment.deleted`: Deployment removed
- `prediction.error`: Prediction request failed

### Webhook Payload

```json
{
  "event": "deployment.ready",
  "timestamp": "2024-01-15T10:35:00Z",
  "data": {
    "deployment_id": "dep-abc123",
    "name": "iris-classifier",
    "endpoint_url": "https://api.serveml.com/api/v1/predict/dep-abc123"
  }
}
```

## SDK Examples

### Python

```python
from serveml import Client

# Initialize client
client = Client(api_key="your-api-key")

# Deploy model
deployment = client.deploy(
    model_path="model.pkl",
    requirements_path="requirements.txt",
    name="my-model"
)

# Make prediction
result = deployment.predict([5.1, 3.5, 1.4, 0.2])
print(result.prediction)

# Get metrics
metrics = deployment.get_metrics(hours=24)
print(f"Total predictions: {metrics.request_count}")
```

### JavaScript/TypeScript

```typescript
import { ServeMLClient } from '@serveml/client';

// Initialize client
const client = new ServeMLClient({ apiKey: 'your-api-key' });

// Deploy model
const deployment = await client.deploy({
  modelFile: modelBuffer,
  requirementsFile: reqBuffer,
  name: 'my-model'
});

// Make prediction
const result = await deployment.predict([5.1, 3.5, 1.4, 0.2]);
console.log(result.prediction);
```

### cURL

```bash
# Deploy model
curl -X POST https://api.serveml.com/api/v1/deploy \
  -H "Authorization: Bearer $TOKEN" \
  -F "model_file=@model.pkl" \
  -F "requirements_file=@requirements.txt" \
  -F "name=iris-classifier"

# Make prediction
curl -X POST https://api.serveml.com/api/v1/predict/dep-abc123 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"data": [5.1, 3.5, 1.4, 0.2]}'
```