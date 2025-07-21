"""
ServeML MVP Backend
Simple FastAPI application for model deployment
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
import os
from typing import Optional, Dict
from datetime import datetime

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


class DeploymentListResponse(BaseModel):
    deployments: list[DeploymentResponse]
    total: int


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "ServeML API is running",
        "version": "0.1.0",
        "status": "healthy"
    }


@app.post("/api/v1/deploy", response_model=DeploymentResponse)
async def deploy_model(
    model_file: UploadFile = File(..., description="Pickled model file (.pkl)"),
    requirements_file: UploadFile = File(..., description="Python requirements.txt"),
    name: Optional[str] = None
):
    """
    Deploy a machine learning model
    
    This endpoint accepts a model file and requirements.txt,
    saves them, and initiates the deployment process.
    """
    # Validate file types
    if not model_file.filename.endswith('.pkl'):
        raise HTTPException(status_code=400, detail="Model file must be a .pkl file")
    
    if not requirements_file.filename.endswith('.txt'):
        raise HTTPException(status_code=400, detail="Requirements file must be a .txt file")
    
    # Generate unique deployment ID
    deployment_id = str(uuid.uuid4())
    deployment_name = name or f"model-{deployment_id[:8]}"
    
    # Create deployment directory
    deployment_dir = os.path.join(UPLOAD_DIR, deployment_id)
    os.makedirs(deployment_dir, exist_ok=True)
    
    try:
        # Save model file
        model_path = os.path.join(deployment_dir, "model.pkl")
        with open(model_path, "wb") as f:
            content = await model_file.read()
            f.write(content)
        
        # Save requirements file
        requirements_path = os.path.join(deployment_dir, "requirements.txt")
        with open(requirements_path, "wb") as f:
            content = await requirements_file.read()
            f.write(content)
        
        # Store deployment info
        deployment_info = {
            "id": deployment_id,
            "name": deployment_name,
            "status": "deploying",
            "created_at": datetime.utcnow().isoformat(),
            "model_path": model_path,
            "requirements_path": requirements_path,
            "endpoint_url": None,
            "error_message": None
        }
        deployments[deployment_id] = deployment_info
        
        # TODO: Trigger deployment pipeline
        # For now, we'll simulate deployment after a delay
        
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)