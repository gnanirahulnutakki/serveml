"""
API Integration Tests
"""
import pytest
import time
from fastapi import status


class TestAPIIntegration:
    """Test complete API workflows"""
    
    def test_health_check(self, test_client):
        """Test health check endpoint"""
        response = test_client.get("/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
    
    def test_complete_deployment_flow(self, test_client, test_model_file, test_requirements_file):
        """Test complete deployment workflow"""
        # 1. Register user
        register_response = test_client.post("/api/v1/auth/register", json={
            "email": "deploy@test.com",
            "username": "deployuser",
            "password": "deploypass123"
        })
        assert register_response.status_code == status.HTTP_200_OK
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Deploy model
        with open(test_model_file, 'rb') as model_f, open(test_requirements_file, 'rb') as req_f:
            files = {
                "model_file": ("model.pkl", model_f, "application/octet-stream"),
                "requirements_file": ("requirements.txt", req_f, "text/plain")
            }
            deploy_response = test_client.post(
                "/api/v1/deploy",
                files=files,
                headers=headers,
                data={"name": "test-deployment"}
            )
        
        assert deploy_response.status_code == status.HTTP_200_OK
        deployment = deploy_response.json()
        assert "id" in deployment
        assert deployment["status"] in ["validating", "building"]
        deployment_id = deployment["id"]
        
        # 3. Check deployment status
        status_response = test_client.get(
            f"/api/v1/deployments/{deployment_id}",
            headers=headers
        )
        assert status_response.status_code == status.HTTP_200_OK
        status_data = status_response.json()
        assert status_data["id"] == deployment_id
        
        # 4. List deployments
        list_response = test_client.get("/api/v1/deployments", headers=headers)
        assert list_response.status_code == status.HTTP_200_OK
        deployments = list_response.json()
        assert deployments["total"] >= 1
        
        # 5. Delete deployment
        delete_response = test_client.delete(
            f"/api/v1/deployments/{deployment_id}",
            headers=headers
        )
        assert delete_response.status_code == status.HTTP_200_OK
    
    def test_authentication_flow(self, test_client):
        """Test authentication workflow"""
        # 1. Register
        register_data = {
            "email": "auth@test.com",
            "username": "authuser",
            "password": "authpass123",
            "full_name": "Auth User"
        }
        register_response = test_client.post("/api/v1/auth/register", json=register_data)
        assert register_response.status_code == status.HTTP_200_OK
        register_result = register_response.json()
        assert "access_token" in register_result
        assert register_result["user"]["email"] == register_data["email"]
        
        # 2. Login
        login_response = test_client.post("/api/v1/auth/login", json={
            "email": register_data["email"],
            "password": register_data["password"]
        })
        assert login_response.status_code == status.HTTP_200_OK
        login_result = login_response.json()
        assert "access_token" in login_result
        
        # 3. Get current user
        headers = {"Authorization": f"Bearer {login_result['access_token']}"}
        me_response = test_client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == status.HTTP_200_OK
        user_data = me_response.json()
        assert user_data["email"] == register_data["email"]
        assert user_data["username"] == register_data["username"]
    
    def test_unauthorized_access(self, test_client):
        """Test unauthorized access to protected endpoints"""
        # Without token
        response = test_client.get("/api/v1/deployments")
        assert response.status_code == status.HTTP_200_OK  # Optional auth
        
        response = test_client.get("/api/v1/auth/me")
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        # With invalid token
        headers = {"Authorization": "Bearer invalid_token"}
        response = test_client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_model_validation_errors(self, test_client, auth_headers):
        """Test model validation error handling"""
        # Invalid file type
        files = {
            "model_file": ("model.txt", b"not a model", "text/plain"),
            "requirements_file": ("requirements.txt", b"numpy", "text/plain")
        }
        response = test_client.post("/api/v1/deploy", files=files, headers=auth_headers)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Model file must be one of" in response.json()["detail"]
    
    def test_metrics_endpoint(self, test_client, auth_headers, sample_deployment_data):
        """Test metrics endpoint"""
        # Add deployment to memory
        from app import deployments
        deployments[sample_deployment_data["id"]] = sample_deployment_data
        
        # Get metrics
        response = test_client.get(
            f"/api/v1/metrics/{sample_deployment_data['id']}?hours=24",
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        metrics = response.json()
        assert "metrics" in metrics
        assert "cost_estimate" in metrics
        assert "dashboard_url" in metrics
    
    def test_test_model_endpoint(self, test_client, auth_headers, sample_deployment_data):
        """Test model testing endpoint"""
        # Add active deployment
        from app import deployments
        sample_deployment_data["status"] = "active"
        deployments[sample_deployment_data["id"]] = sample_deployment_data
        
        # Test model
        response = test_client.post("/api/v1/test-model", json={
            "deployment_id": sample_deployment_data["id"],
            "data": {"feature1": 5.1, "feature2": 3.5, "feature3": 1.4, "feature4": 0.2}
        }, headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        result = response.json()
        assert "output" in result
        assert "prediction" in result["output"]