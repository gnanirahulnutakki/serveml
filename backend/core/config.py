"""
Configuration settings for ServeML
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    app_name: str = "ServeML"
    app_version: str = "0.1.0"
    debug: bool = False
    
    # Security
    secret_key: str = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours
    
    # AWS
    aws_region: str = "us-east-1"
    s3_bucket: str = os.environ.get("S3_BUCKET", "serveml-uploads")
    dynamodb_table: str = os.environ.get("DYNAMODB_TABLE", "serveml-deployments")
    ecr_repository: str = os.environ.get("ECR_REPOSITORY", "serveml-models")
    
    # Database
    database_url: Optional[str] = os.environ.get("DATABASE_URL")
    
    # CORS
    cors_origins: list = ["http://localhost:3000", "http://localhost:8000"]
    
    # File limits
    max_upload_size: int = 500 * 1024 * 1024  # 500MB
    allowed_model_extensions: list = [".pkl", ".pt", ".pth", ".h5", ".keras"]
    
    # Deployment
    deployment_timeout: int = 600  # 10 minutes
    max_deployments_per_user: int = 10
    
    # Monitoring
    enable_metrics: bool = True
    metrics_retention_days: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Create global settings instance
settings = Settings()