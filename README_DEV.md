# ServeML Development Guide

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js (optional, for frontend tooling)
- Docker (optional, for containerized development)

### Setup and Run

#### Option 1: Using Make (Recommended)
```bash
# Set up environment and create test model
make setup

# Run both backend and frontend
make run

# Or run separately
make run-backend  # In one terminal
make run-frontend # In another terminal
```

#### Option 2: Manual Setup
```bash
# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run backend
uvicorn app:app --reload

# In another terminal, run frontend
cd frontend
python -m http.server 3000
```

#### Option 3: Using Docker
```bash
docker-compose up
```

### Access the Application
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Testing the Application

1. **Create a test model:**
   ```bash
   python create_test_model.py
   ```
   This creates:
   - `test_models/iris_model.pkl` - A trained scikit-learn model
   - `test_models/requirements.txt` - Python dependencies
   - `test_models/sample_prediction.py` - Example prediction code

2. **Upload the model:**
   - Open http://localhost:3000
   - Enter a model name (optional)
   - Select `iris_model.pkl` for the model file
   - Select `requirements.txt` for the requirements file
   - Click "Deploy Model"

3. **Monitor deployment:**
   - Watch the status change from "deploying" to "active"
   - After ~30 seconds (simulated), you'll see the endpoint URL

## API Endpoints

### Deploy a Model
```bash
curl -X POST http://localhost:8000/api/v1/deploy \
  -F "model_file=@test_models/iris_model.pkl" \
  -F "requirements_file=@test_models/requirements.txt" \
  -F "name=my-iris-model"
```

### List Deployments
```bash
curl http://localhost:8000/api/v1/deployments
```

### Get Deployment Status
```bash
curl http://localhost:8000/api/v1/deployments/{deployment_id}
```

### Delete Deployment
```bash
curl -X DELETE http://localhost:8000/api/v1/deployments/{deployment_id}
```

## Project Structure

```
serveml/
├── backend/
│   ├── app.py              # FastAPI application
│   ├── requirements.txt    # Python dependencies
│   ├── uploads/           # Uploaded model files
│   └── templates/         # Docker/wrapper templates
├── frontend/
│   ├── index.html         # Main UI
│   ├── app.js            # Frontend logic
│   └── style.css         # Styling
├── create_test_model.py   # Test model generator
├── docker-compose.yml     # Docker setup
└── Makefile              # Development commands
```

## Development Tips

1. **Backend Development:**
   - FastAPI auto-reloads on code changes
   - Check API docs at http://localhost:8000/docs
   - Logs appear in the terminal

2. **Frontend Development:**
   - Refresh browser to see changes
   - Check browser console for errors
   - Network tab shows API calls

3. **Testing Different Models:**
   - Create different sklearn models
   - Try various requirements.txt configurations
   - Test error cases (wrong file types, etc.)

## Next Steps

1. **Add Model Serving:**
   - Create Docker wrapper template
   - Implement actual prediction endpoint
   - Add model validation

2. **AWS Integration:**
   - Set up S3 for file storage
   - Configure Lambda deployment
   - Add DynamoDB for persistence

3. **Authentication:**
   - Add user registration/login
   - Implement JWT tokens
   - Secure API endpoints

## Troubleshooting

### CORS Issues
If you see CORS errors, ensure the backend has CORS middleware enabled and is running on port 8000.

### File Upload Errors
- Check file size limits (100MB for models)
- Ensure correct file extensions (.pkl, .txt)
- Verify uploads directory exists

### Port Already in Use
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Kill process on port 3000
lsof -ti:3000 | xargs kill -9
```

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines on contributing to ServeML.