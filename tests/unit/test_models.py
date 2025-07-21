"""
Unit tests for data models
"""
import pytest
from datetime import datetime
from pydantic import ValidationError
from models import UserCreate, UserLogin, DeploymentRequest, DeploymentResponse, DeploymentStatus


class TestUserModels:
    """Test user-related models"""
    
    def test_user_create_valid(self):
        """Test creating valid user"""
        user = UserCreate(
            email="test@example.com",
            username="testuser",
            password="password123",
            full_name="Test User"
        )
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.full_name == "Test User"
    
    def test_user_create_invalid_email(self):
        """Test invalid email validation"""
        with pytest.raises(ValidationError):
            UserCreate(
                email="invalid-email",
                username="testuser",
                password="password123"
            )
    
    def test_user_create_missing_required(self):
        """Test missing required fields"""
        with pytest.raises(ValidationError):
            UserCreate(email="test@example.com")
    
    def test_user_login(self):
        """Test user login model"""
        login = UserLogin(
            email="test@example.com",
            password="password123"
        )
        assert login.email == "test@example.com"
        assert login.password == "password123"


class TestDeploymentModels:
    """Test deployment-related models"""
    
    def test_deployment_request(self):
        """Test deployment request model"""
        req = DeploymentRequest(
            name="test-model",
            framework="sklearn"
        )
        assert req.name == "test-model"
        assert req.framework == "sklearn"
    
    def test_deployment_response(self):
        """Test deployment response model"""
        resp = DeploymentResponse(
            id="deploy-123",
            name="test-model",
            status=DeploymentStatus.BUILDING,
            created_at=datetime.utcnow(),
            user_id="user-123"
        )
        assert resp.id == "deploy-123"
        assert resp.status == DeploymentStatus.BUILDING
        assert resp.user_id == "user-123"
    
    def test_deployment_status_enum(self):
        """Test deployment status enum"""
        assert DeploymentStatus.VALIDATING.value == "validating"
        assert DeploymentStatus.BUILDING.value == "building"
        assert DeploymentStatus.DEPLOYING.value == "deploying"
        assert DeploymentStatus.ACTIVE.value == "active"
        assert DeploymentStatus.FAILED.value == "failed"
        assert DeploymentStatus.DELETED.value == "deleted"