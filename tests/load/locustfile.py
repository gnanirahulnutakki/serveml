"""
Load Testing with Locust
"""
from locust import HttpUser, task, between
import random
import base64
import os


class ServeMLUser(HttpUser):
    """Load test user for ServeML platform"""
    wait_time = between(1, 5)
    
    def on_start(self):
        """Setup before running tasks"""
        # Register and login
        self.register_and_login()
        self.deployment_ids = []
    
    def register_and_login(self):
        """Register a new user and get auth token"""
        username = f"loadtest_{random.randint(1000, 9999)}"
        response = self.client.post("/api/v1/auth/register", json={
            "email": f"{username}@loadtest.com",
            "username": username,
            "password": "loadtest123"
        })
        
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.headers = {}
    
    @task(3)
    def view_deployments(self):
        """View deployment list"""
        self.client.get("/api/v1/deployments", headers=self.headers)
    
    @task(2)
    def deploy_model(self):
        """Deploy a model"""
        # Create minimal model file
        model_content = b"fake_model_for_load_testing"
        requirements_content = b"scikit-learn==1.3.0\nnumpy==1.24.3"
        
        files = {
            "model_file": ("model.pkl", model_content, "application/octet-stream"),
            "requirements_file": ("requirements.txt", requirements_content, "text/plain")
        }
        
        response = self.client.post(
            "/api/v1/deploy",
            files=files,
            headers=self.headers,
            data={"name": f"load-test-{random.randint(1000, 9999)}"}
        )
        
        if response.status_code == 200:
            deployment_id = response.json()["id"]
            self.deployment_ids.append(deployment_id)
    
    @task(4)
    def check_deployment_status(self):
        """Check status of a deployment"""
        if self.deployment_ids:
            deployment_id = random.choice(self.deployment_ids)
            self.client.get(
                f"/api/v1/deployments/{deployment_id}",
                headers=self.headers
            )
    
    @task(2)
    def test_model_prediction(self):
        """Test model prediction"""
        if self.deployment_ids:
            deployment_id = random.choice(self.deployment_ids)
            
            # Iris dataset features
            test_data = {
                "deployment_id": deployment_id,
                "data": {
                    "feature1": random.uniform(4.0, 8.0),
                    "feature2": random.uniform(2.0, 5.0),
                    "feature3": random.uniform(1.0, 7.0),
                    "feature4": random.uniform(0.1, 3.0)
                }
            }
            
            self.client.post(
                "/api/v1/test-model",
                json=test_data,
                headers=self.headers
            )
    
    @task(1)
    def view_metrics(self):
        """View deployment metrics"""
        if self.deployment_ids:
            deployment_id = random.choice(self.deployment_ids)
            self.client.get(
                f"/api/v1/metrics/{deployment_id}?hours=24",
                headers=self.headers
            )
    
    @task(1)
    def health_check(self):
        """Health check endpoint"""
        self.client.get("/")


class AdminUser(HttpUser):
    """Admin user for monitoring tasks"""
    wait_time = between(5, 10)
    
    def on_start(self):
        """Setup admin user"""
        # Login as admin (assuming admin exists)
        response = self.client.post("/api/v1/auth/login", json={
            "email": "admin@serveml.com",
            "password": "admin123"
        })
        
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.headers = {}
    
    @task
    def view_all_deployments(self):
        """View all deployments with pagination"""
        self.client.get("/api/v1/deployments?limit=50", headers=self.headers)
    
    @task
    def search_deployments(self):
        """Search deployments"""
        search_terms = ["test", "iris", "model", "sklearn"]
        term = random.choice(search_terms)
        self.client.get(f"/api/v1/deployments?search={term}", headers=self.headers)


class WebsiteUser(HttpUser):
    """User browsing the website"""
    wait_time = between(2, 8)
    
    @task(5)
    def view_homepage(self):
        """View homepage"""
        self.client.get("/")
    
    @task(2)
    def view_docs(self):
        """View documentation"""
        # Simulate viewing static docs
        self.client.get("/docs")
    
    @task(1)
    def view_pricing(self):
        """View pricing page"""
        # Simulate viewing pricing
        self.client.get("/api/v1/pricing")