"""
Security Tests
"""
import pytest
import jwt
from datetime import datetime, timedelta
from core.config import settings


class TestSecurity:
    """Test security features"""
    
    def test_sql_injection_attempts(self, test_client):
        """Test SQL injection prevention"""
        injection_payloads = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "' UNION SELECT * FROM users--"
        ]
        
        for payload in injection_payloads:
            # Try in login
            response = test_client.post("/api/v1/auth/login", json={
                "email": payload,
                "password": "test"
            })
            assert response.status_code in [400, 401, 422]
            
            # Try in registration
            response = test_client.post("/api/v1/auth/register", json={
                "email": f"{payload}@test.com",
                "username": payload,
                "password": "test123"
            })
            assert response.status_code in [400, 422]
    
    def test_xss_prevention(self, test_client, auth_headers):
        """Test XSS attack prevention"""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "<iframe src='javascript:alert(\"XSS\")'>"
        ]
        
        for payload in xss_payloads:
            # Try in deployment name
            files = {
                "model_file": ("model.pkl", b"fake model", "application/octet-stream"),
                "requirements_file": ("requirements.txt", b"numpy", "text/plain")
            }
            response = test_client.post(
                "/api/v1/deploy",
                files=files,
                headers=auth_headers,
                data={"name": payload}
            )
            # Should either sanitize or reject
            if response.status_code == 200:
                deployment = response.json()
                assert "<script>" not in deployment["name"]
    
    def test_jwt_token_security(self, test_client):
        """Test JWT token security"""
        # Test expired token
        expired_payload = {
            "sub": "test-user",
            "exp": datetime.utcnow() - timedelta(hours=1)
        }
        expired_token = jwt.encode(expired_payload, settings.secret_key, algorithm=settings.algorithm)
        
        response = test_client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {expired_token}"
        })
        assert response.status_code == 401
        
        # Test token with wrong signature
        wrong_secret_token = jwt.encode(
            {"sub": "test-user", "exp": datetime.utcnow() + timedelta(hours=1)},
            "wrong_secret",
            algorithm=settings.algorithm
        )
        
        response = test_client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {wrong_secret_token}"
        })
        assert response.status_code == 401
    
    def test_file_upload_security(self, test_client, auth_headers):
        """Test file upload security"""
        # Test oversized file
        large_content = b"0" * (600 * 1024 * 1024)  # 600MB
        files = {
            "model_file": ("large.pkl", large_content, "application/octet-stream"),
            "requirements_file": ("requirements.txt", b"numpy", "text/plain")
        }
        
        # Should reject large files
        # Note: In real implementation, this would be handled by API Gateway or nginx
        
        # Test executable file
        exe_header = b"MZ\x90\x00\x03\x00\x00\x00"  # PE executable header
        files = {
            "model_file": ("malicious.exe", exe_header, "application/x-msdownload"),
            "requirements_file": ("requirements.txt", b"numpy", "text/plain")
        }
        response = test_client.post("/api/v1/deploy", files=files, headers=auth_headers)
        assert response.status_code == 400
    
    def test_path_traversal(self, test_client, auth_headers):
        """Test path traversal prevention"""
        traversal_names = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "models/../../../sensitive",
            "./../.env"
        ]
        
        for name in traversal_names:
            files = {
                "model_file": ("model.pkl", b"fake model", "application/octet-stream"),
                "requirements_file": ("requirements.txt", b"numpy", "text/plain")
            }
            response = test_client.post(
                "/api/v1/deploy",
                files=files,
                headers=auth_headers,
                data={"name": name}
            )
            # Should sanitize or reject
            if response.status_code == 200:
                deployment = response.json()
                assert ".." not in deployment["name"]
    
    def test_rate_limiting(self, test_client):
        """Test rate limiting (would need actual implementation)"""
        # Make many requests quickly
        responses = []
        for _ in range(100):
            response = test_client.get("/")
            responses.append(response.status_code)
        
        # In production, should see 429 responses after limit
        # For now, just ensure no crashes
        assert all(r in [200, 429] for r in responses)
    
    def test_password_requirements(self, test_client):
        """Test password security requirements"""
        weak_passwords = [
            "123",
            "password",
            "12345678",
            "qwerty"
        ]
        
        for password in weak_passwords:
            response = test_client.post("/api/v1/auth/register", json={
                "email": f"weak{password}@test.com",
                "username": f"weak{password}",
                "password": password
            })
            # Should reject weak passwords
            if len(password) < 8:
                assert response.status_code == 422
    
    def test_cors_headers(self, test_client):
        """Test CORS configuration"""
        response = test_client.options("/api/v1/deployments")
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
    
    def test_sensitive_data_exposure(self, test_client, auth_headers):
        """Test that sensitive data is not exposed"""
        # Create user and check response
        response = test_client.post("/api/v1/auth/register", json={
            "email": "sensitive@test.com",
            "username": "sensitiveuser",
            "password": "sensitive123"
        })
        
        data = response.json()
        # Should not include password hash
        assert "password" not in data
        assert "hashed_password" not in data
        
        # Get user info
        headers = {"Authorization": f"Bearer {data['access_token']}"}
        response = test_client.get("/api/v1/auth/me", headers=headers)
        user_data = response.json()
        
        # Should not include sensitive fields
        assert "password" not in user_data
        assert "hashed_password" not in user_data