"""
End-to-End Tests for ServeML
"""
import pytest
import time
import requests
import subprocess
import os
from pathlib import Path


class TestEndToEnd:
    """Complete end-to-end testing scenarios"""
    
    @classmethod
    def setup_class(cls):
        """Setup test environment"""
        cls.base_url = os.getenv("TEST_BASE_URL", "http://localhost:8000")
        cls.test_user = {
            "email": "e2e@serveml.com",
            "username": "e2euser",
            "password": "e2epass123"
        }
    
    def test_complete_user_journey(self):
        """Test complete user journey from registration to model deployment"""
        
        # 1. User visits homepage
        response = requests.get(f"{self.base_url}/")
        assert response.status_code == 200
        assert "ServeML" in response.json()["message"]
        
        # 2. User registers
        register_response = requests.post(
            f"{self.base_url}/api/v1/auth/register",
            json=self.test_user
        )
        assert register_response.status_code == 200
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 3. User uploads and deploys a model
        model_path = Path("test_models/iris_logistic.pkl")
        req_path = Path("test_models/requirements_minimal.txt")
        
        with open(model_path, "rb") as model_f, open(req_path, "rb") as req_f:
            files = {
                "model_file": ("model.pkl", model_f, "application/octet-stream"),
                "requirements_file": ("requirements.txt", req_f, "text/plain")
            }
            deploy_response = requests.post(
                f"{self.base_url}/api/v1/deploy",
                files=files,
                headers=headers,
                data={"name": "e2e-iris-model"}
            )
        
        assert deploy_response.status_code == 200
        deployment = deploy_response.json()
        deployment_id = deployment["id"]
        
        # 4. User checks deployment status
        max_retries = 30
        for i in range(max_retries):
            status_response = requests.get(
                f"{self.base_url}/api/v1/deployments/{deployment_id}",
                headers=headers
            )
            assert status_response.status_code == 200
            
            status = status_response.json()["status"]
            if status == "active":
                break
            elif status in ["failed", "error"]:
                pytest.fail(f"Deployment failed with status: {status}")
            
            time.sleep(10)  # Wait 10 seconds between checks
        else:
            pytest.fail("Deployment did not become active within timeout")
        
        # 5. User tests the deployed model
        test_response = requests.post(
            f"{self.base_url}/api/v1/test-model",
            json={
                "deployment_id": deployment_id,
                "data": {
                    "feature1": 5.1,
                    "feature2": 3.5,
                    "feature3": 1.4,
                    "feature4": 0.2
                }
            },
            headers=headers
        )
        assert test_response.status_code == 200
        assert "output" in test_response.json()
        
        # 6. User views metrics
        metrics_response = requests.get(
            f"{self.base_url}/api/v1/metrics/{deployment_id}?hours=1",
            headers=headers
        )
        assert metrics_response.status_code == 200
        metrics = metrics_response.json()
        assert "metrics" in metrics
        assert "cost_estimate" in metrics
        
        # 7. User lists all deployments
        list_response = requests.get(
            f"{self.base_url}/api/v1/deployments",
            headers=headers
        )
        assert list_response.status_code == 200
        deployments = list_response.json()
        assert deployments["total"] >= 1
        assert any(d["id"] == deployment_id for d in deployments["items"])
        
        # 8. User deletes deployment
        delete_response = requests.delete(
            f"{self.base_url}/api/v1/deployments/{deployment_id}",
            headers=headers
        )
        assert delete_response.status_code == 200
    
    def test_multiple_framework_deployments(self):
        """Test deploying models from different frameworks"""
        
        # Login
        login_response = requests.post(
            f"{self.base_url}/api/v1/auth/login",
            json={
                "email": self.test_user["email"],
                "password": self.test_user["password"]
            }
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        frameworks = [
            ("iris_logistic.pkl", "requirements_sklearn_full.txt", "sklearn"),
            ("iris_torch.pt", "requirements_pytorch.txt", "pytorch"),
            ("iris_tf.h5", "requirements_tensorflow.txt", "tensorflow")
        ]
        
        deployment_ids = []
        
        for model_file, req_file, framework in frameworks:
            model_path = Path(f"test_models/{model_file}")
            req_path = Path(f"test_models/{req_file}")
            
            if not model_path.exists():
                continue  # Skip if framework not installed
            
            with open(model_path, "rb") as model_f, open(req_path, "rb") as req_f:
                files = {
                    "model_file": (model_file, model_f, "application/octet-stream"),
                    "requirements_file": ("requirements.txt", req_f, "text/plain")
                }
                
                deploy_response = requests.post(
                    f"{self.base_url}/api/v1/deploy",
                    files=files,
                    headers=headers,
                    data={"name": f"e2e-{framework}-model"}
                )
            
            assert deploy_response.status_code == 200
            deployment_ids.append(deploy_response.json()["id"])
        
        # Verify all deployments
        for deployment_id in deployment_ids:
            status_response = requests.get(
                f"{self.base_url}/api/v1/deployments/{deployment_id}",
                headers=headers
            )
            assert status_response.status_code == 200
    
    def test_concurrent_deployments(self):
        """Test multiple concurrent deployments"""
        import concurrent.futures
        
        # Login
        login_response = requests.post(
            f"{self.base_url}/api/v1/auth/login",
            json={
                "email": self.test_user["email"],
                "password": self.test_user["password"]
            }
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        def deploy_model(index):
            model_path = Path("test_models/iris_logistic.pkl")
            req_path = Path("test_models/requirements_minimal.txt")
            
            with open(model_path, "rb") as model_f, open(req_path, "rb") as req_f:
                files = {
                    "model_file": ("model.pkl", model_f, "application/octet-stream"),
                    "requirements_file": ("requirements.txt", req_f, "text/plain")
                }
                
                response = requests.post(
                    f"{self.base_url}/api/v1/deploy",
                    files=files,
                    headers=headers,
                    data={"name": f"concurrent-model-{index}"}
                )
            
            return response.status_code == 200, response.json() if response.status_code == 200 else None
        
        # Deploy 5 models concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(deploy_model, i) for i in range(5)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        # Verify all deployments succeeded
        successful = sum(1 for success, _ in results if success)
        assert successful >= 4  # Allow 1 failure due to rate limiting
    
    def test_error_recovery(self):
        """Test system behavior under error conditions"""
        
        # Login
        login_response = requests.post(
            f"{self.base_url}/api/v1/auth/login",
            json={
                "email": self.test_user["email"],
                "password": self.test_user["password"]
            }
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test 1: Invalid model file
        files = {
            "model_file": ("model.txt", b"not a model", "text/plain"),
            "requirements_file": ("requirements.txt", b"numpy", "text/plain")
        }
        
        response = requests.post(
            f"{self.base_url}/api/v1/deploy",
            files=files,
            headers=headers
        )
        assert response.status_code == 400
        
        # Test 2: Missing requirements
        model_path = Path("test_models/iris_logistic.pkl")
        with open(model_path, "rb") as model_f:
            files = {
                "model_file": ("model.pkl", model_f, "application/octet-stream")
            }
            
            response = requests.post(
                f"{self.base_url}/api/v1/deploy",
                files=files,
                headers=headers
            )
        assert response.status_code == 422
        
        # Test 3: Invalid requirements
        req_path = Path("test_models/requirements_invalid.txt")
        with open(model_path, "rb") as model_f, open(req_path, "rb") as req_f:
            files = {
                "model_file": ("model.pkl", model_f, "application/octet-stream"),
                "requirements_file": ("requirements.txt", req_f, "text/plain")
            }
            
            response = requests.post(
                f"{self.base_url}/api/v1/deploy",
                files=files,
                headers=headers
            )
        
        # Should accept but fail during build
        if response.status_code == 200:
            deployment_id = response.json()["id"]
            
            # Wait and check status
            time.sleep(30)
            status_response = requests.get(
                f"{self.base_url}/api/v1/deployments/{deployment_id}",
                headers=headers
            )
            assert status_response.json()["status"] in ["failed", "error"]