"""
ServeML MVP Backend
Simple FastAPI application for model deployment
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uuid
import os
from typing import Optional, Dict, List
from datetime import datetime
import asyncio
import logging

# Import our services
from services.model_validator import ModelValidator
from services.docker_builder import DockerBuilder
from services.s3_service import S3Service

# Import core components
from core.config import settings
from core.security import AuthService, get_current_user, get_optional_current_user

# Import models
from models.user import UserCreate, UserLogin, UserResponse, TokenResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ServeML MVP",
    description="One-click ML model deployment platform",
    version="0.1.0"
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for MVP (will be replaced with DynamoDB)
deployments: Dict[str, dict] = {}

# Ensure uploads directory exists
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class DeploymentResponse(BaseModel):
    id: str
    name: str
    status: str
    created_at: str
    endpoint_url: Optional[str] = None
    error_message: Optional[str] = None
    model_metadata: Optional[Dict] = None


class DeploymentListResponse(BaseModel):
    deployments: list[DeploymentResponse]
    total: int


class ModelTestRequest(BaseModel):
    deployment_id: str
    data: Dict = Field(..., description="Input data for prediction")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "ServeML API is running",
        "version": settings.app_version,
        "status": "healthy",
        "authenticated": False  # Public endpoint
    }


# In-memory user storage for MVP (replace with database in production)
users_db = {}


@app.post("/api/v1/auth/register", response_model=TokenResponse)
async def register(user: UserCreate):
    """Register a new user"""
    # Check if user exists
    if user.email in users_db:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Create user
    user_id = str(uuid.uuid4())
    hashed_password = AuthService.get_password_hash(user.password)
    
    users_db[user.email] = {
        "user_id": user_id,
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "hashed_password": hashed_password,
        "is_active": True,
        "created_at": datetime.utcnow()
    }
    
    # Create access token
    access_token = AuthService.create_access_token(
        data={
            "sub": user_id,
            "email": user.email,
            "username": user.username
        }
    )
    
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserResponse(
            user_id=user_id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            is_active=True,
            created_at=datetime.utcnow()
        )
    )


@app.post("/api/v1/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """Login user"""
    # Find user
    user = users_db.get(credentials.email)
    
    if not user or not AuthService.verify_password(
        credentials.password, user["hashed_password"]
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password"
        )
    
    # Create access token
    access_token = AuthService.create_access_token(
        data={
            "sub": user["user_id"],
            "email": user["email"],
            "username": user["username"]
        }
    )
    
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserResponse(
            user_id=user["user_id"],
            email=user["email"],
            username=user["username"],
            full_name=user.get("full_name"),
            is_active=user["is_active"],
            created_at=user["created_at"]
        )
    )


@app.get("/api/v1/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: Dict = Depends(get_current_user)):
    """Get current user information"""
    # In production, fetch from database
    user = None
    for email, user_data in users_db.items():
        if user_data["user_id"] == current_user["user_id"]:
            user = user_data
            break
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(
        user_id=user["user_id"],
        email=user["email"],
        username=user["username"],
        full_name=user.get("full_name"),
        is_active=user["is_active"],
        created_at=user["created_at"]
    )


@app.post("/api/v1/deploy", response_model=DeploymentResponse)
async def deploy_model(
    background_tasks: BackgroundTasks,
    model_file: UploadFile = File(..., description="Pickled model file (.pkl)"),
    requirements_file: UploadFile = File(..., description="Python requirements.txt"),
    name: Optional[str] = None,
    current_user: Optional[Dict] = Depends(get_optional_current_user)
):
    """
    Deploy a machine learning model
    
    This endpoint accepts a model file and requirements.txt,
    saves them, validates them, and initiates the deployment process.
    """
    # Validate file types
    supported_extensions = ['.pkl', '.pt', '.pth', '.h5', '.keras']
    file_ext = os.path.splitext(model_file.filename)[1].lower()
    
    if file_ext not in supported_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Model file must be one of: {', '.join(supported_extensions)}"
        )
    
    if not requirements_file.filename.endswith('.txt'):
        raise HTTPException(status_code=400, detail="Requirements file must be a .txt file")
    
    # Generate unique deployment ID
    deployment_id = str(uuid.uuid4())
    deployment_name = name or f"model-{deployment_id[:8]}"
    
    # Create deployment directory
    deployment_dir = os.path.join(UPLOAD_DIR, deployment_id)
    os.makedirs(deployment_dir, exist_ok=True)
    
    try:
        # Save model file with original extension
        model_filename = f"model{file_ext}"
        model_path = os.path.join(deployment_dir, model_filename)
        with open(model_path, "wb") as f:
            content = await model_file.read()
            f.write(content)
        
        # Save requirements file
        requirements_path = os.path.join(deployment_dir, "requirements.txt")
        with open(requirements_path, "wb") as f:
            content = await requirements_file.read()
            f.write(content)
        
        # Validate model
        validator = ModelValidator()
        is_valid, model_metadata = validator.validate_model(model_path)
        
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"Model validation failed: {', '.join(model_metadata.get('errors', ['Unknown error']))}"
            )
        
        # Validate requirements
        req_valid, req_metadata = validator.validate_requirements(requirements_path)
        if not req_valid:
            logger.warning(f"Requirements validation warnings: {req_metadata}")
        
        # Store deployment info
        deployment_info = {
            "id": deployment_id,
            "name": deployment_name,
            "status": "validating",
            "created_at": datetime.utcnow().isoformat(),
            "model_path": model_path,
            "requirements_path": requirements_path,
            "endpoint_url": None,
            "error_message": None,
            "model_metadata": model_metadata
        }
        deployments[deployment_id] = deployment_info
        
        # Start background deployment process
        background_tasks.add_task(
            deploy_model_background,
            deployment_id,
            model_path,
            requirements_path,
            model_metadata
        )
        
        return DeploymentResponse(**deployment_info)
        
    except Exception as e:
        # Clean up on error
        if os.path.exists(deployment_dir):
            import shutil
            shutil.rmtree(deployment_dir)
        
        raise HTTPException(status_code=500, detail=f"Deployment failed: {str(e)}")


@app.get("/api/v1/deployments", response_model=DeploymentListResponse)
async def list_deployments():
    """List all deployments"""
    deployment_list = list(deployments.values())
    # Sort by created_at descending
    deployment_list.sort(key=lambda x: x["created_at"], reverse=True)
    
    return DeploymentListResponse(
        deployments=[DeploymentResponse(**d) for d in deployment_list],
        total=len(deployment_list)
    )


@app.get("/api/v1/deployments/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(deployment_id: str):
    """Get deployment status and details"""
    if deployment_id not in deployments:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    deployment = deployments[deployment_id]
    
    # Simulate deployment completion for MVP
    # In production, this would check actual deployment status
    if deployment["status"] == "deploying":
        # Check if enough time has passed (simulate 30 second deployment)
        created_at = datetime.fromisoformat(deployment["created_at"])
        if (datetime.utcnow() - created_at).seconds > 30:
            deployment["status"] = "active"
            deployment["endpoint_url"] = f"https://api.serveml.com/models/{deployment_id}/predict"
    
    return DeploymentResponse(**deployment)


@app.delete("/api/v1/deployments/{deployment_id}")
async def delete_deployment(deployment_id: str):
    """Delete a deployment"""
    if deployment_id not in deployments:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    deployment = deployments[deployment_id]
    
    # Clean up files
    deployment_dir = os.path.join(UPLOAD_DIR, deployment_id)
    if os.path.exists(deployment_dir):
        import shutil
        shutil.rmtree(deployment_dir)
    
    # Remove from storage
    del deployments[deployment_id]
    
    return {"message": "Deployment deleted successfully", "deployment_id": deployment_id}


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "deployments_count": len(deployments),
        "upload_dir_exists": os.path.exists(UPLOAD_DIR)
    }


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {"error": "Not found", "detail": str(exc.detail)}


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return {"error": "Internal server error", "detail": "An unexpected error occurred"}


async def deploy_model_background(
    deployment_id: str,
    model_path: str,
    requirements_path: str,
    model_metadata: Dict
):
    """Background task to deploy model"""
    try:
        # Update status to building
        if deployment_id in deployments:
            deployments[deployment_id]["status"] = "building"
            
        # Initialize Docker builder
        docker_builder = DockerBuilder()
        
        # Validate requirements
        is_valid, validation_result = docker_builder.validate_requirements(requirements_path)
        if not is_valid:
            raise Exception(f"Invalid requirements: {validation_result}")
        
        # Build Docker image
        logger.info(f"Building Docker image for deployment {deployment_id}")
        success, result = docker_builder.build_image(
            model_path=model_path,
            requirements_path=requirements_path,
            deployment_id=deployment_id,
            framework=model_metadata.get('framework', 'sklearn')
        )
        
        if not success:
            raise Exception(f"Docker build failed: {result}")
        
        # Update status to deploying
        if deployment_id in deployments:
            deployments[deployment_id]["status"] = "deploying"
            deployments[deployment_id]["docker_image"] = result
        
        # Simulate deployment delay
        await asyncio.sleep(10)
        
        # Update to active
        if deployment_id in deployments:
            deployments[deployment_id]["status"] = "active"
            deployments[deployment_id]["endpoint_url"] = f"https://api.serveml.com/models/{deployment_id}/predict"
            
        logger.info(f"Deployment {deployment_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Deployment {deployment_id} failed: {str(e)}")
        if deployment_id in deployments:
            deployments[deployment_id]["status"] = "failed"
            deployments[deployment_id]["error_message"] = str(e)


@app.post("/api/v1/test-model")
async def test_model(request: ModelTestRequest):
    """Test a deployed model with sample data"""
    deployment = deployments.get(request.deployment_id)
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    if deployment["status"] != "active":
        raise HTTPException(
            status_code=400, 
            detail=f"Model not ready. Current status: {deployment['status']}"
        )
    
    # For MVP, return simulated prediction
    # In production, this would call the actual Lambda endpoint
    model_metadata = deployment.get("model_metadata", {})
    
    # Generate mock prediction based on model type
    if model_metadata.get("framework") == "sklearn":
        # Simulate classification
        prediction = {
            "prediction": [0],
            "probability": [[0.7, 0.2, 0.1]],
            "model_type": model_metadata.get("model_type", "Unknown")
        }
    else:
        # Generic prediction
        prediction = {
            "prediction": [42.0],
            "model_type": model_metadata.get("model_type", "Unknown")
        }
    
    return {
        "deployment_id": request.deployment_id,
        "input": request.data,
        "output": prediction,
        "model_metadata": model_metadata
    }


@app.get("/api/v1/validate-model")
async def validate_model_endpoint(model_path: str):
    """Validate a model file (for testing)"""
    validator = ModelValidator()
    is_valid, metadata = validator.validate_model(model_path)
    
    return {
        "valid": is_valid,
        "metadata": metadata
    }


@app.get("/api/v1/metrics/{deployment_id}")
async def get_deployment_metrics(
    deployment_id: str,
    hours: int = 24,
    current_user: Optional[Dict] = Depends(get_optional_current_user)
):
    """Get metrics for a deployment"""
    deployment = deployments.get(deployment_id)
    
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    # Check authorization if user is authenticated
    if current_user and deployment.get("user_id") != current_user.get("user_id"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # For MVP, return mock metrics
    from services.metrics_service import MetricsService
    metrics_service = MetricsService()
    
    start_time = datetime.utcnow() - timedelta(hours=hours)
    metrics = metrics_service.get_deployment_metrics(
        deployment_id=deployment_id,
        start_time=start_time
    )
    
    # Add cost estimate
    cost_estimate = metrics_service.create_cost_estimate(
        deployment.get("model_metadata", {})
    )
    
    return {
        "deployment_id": deployment_id,
        "period_hours": hours,
        "metrics": metrics.get("summary", {}),
        "cost_estimate": cost_estimate,
        "dashboard_url": metrics_service.create_dashboard_link(deployment_id)
    }


@app.get("/api/v1/usage")
async def get_usage_stats(current_user: Dict = Depends(get_current_user)):
    """Get usage statistics for current user"""
    from services.metrics_service import MetricsService
    metrics_service = MetricsService()
    
    usage_stats = metrics_service.get_usage_stats(current_user["user_id"])
    
    return {
        "user_id": current_user["user_id"],
        "usage": usage_stats,
        "limits": {
            "max_deployments": settings.max_deployments_per_user,
            "max_model_size_mb": settings.max_upload_size / (1024 * 1024)
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)