"""
Unit tests for authentication
"""
import pytest
from datetime import datetime, timedelta
import jwt
from auth import create_access_token, verify_password, get_password_hash
from core.config import settings


class TestAuthentication:
    """Test authentication functions"""
    
    def test_password_hashing(self):
        """Test password hashing and verification"""
        password = "testpassword123"
        hashed = get_password_hash(password)
        
        # Hash should be different from original
        assert hashed != password
        
        # Should verify correctly
        assert verify_password(password, hashed) is True
        
        # Wrong password should fail
        assert verify_password("wrongpassword", hashed) is False
    
    def test_create_access_token(self):
        """Test JWT token creation"""
        user_data = {"sub": "testuser"}
        token = create_access_token(user_data)
        
        # Decode token
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        
        assert payload["sub"] == "testuser"
        assert "exp" in payload
        
        # Check expiration time
        exp_time = datetime.fromtimestamp(payload["exp"])
        current_time = datetime.utcnow()
        
        # Token should expire in about 30 minutes
        time_diff = exp_time - current_time
        assert timedelta(minutes=29) < time_diff < timedelta(minutes=31)
    
    def test_create_access_token_custom_expiry(self):
        """Test token creation with custom expiry"""
        user_data = {"sub": "testuser"}
        expires_delta = timedelta(hours=1)
        token = create_access_token(user_data, expires_delta)
        
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        exp_time = datetime.fromtimestamp(payload["exp"])
        current_time = datetime.utcnow()
        
        time_diff = exp_time - current_time
        assert timedelta(minutes=59) < time_diff < timedelta(minutes=61)
    
    def test_token_decode_invalid(self):
        """Test decoding invalid token"""
        invalid_token = "invalid.token.here"
        
        with pytest.raises(jwt.InvalidTokenError):
            jwt.decode(invalid_token, settings.secret_key, algorithms=[settings.algorithm])
    
    def test_token_decode_wrong_secret(self):
        """Test decoding token with wrong secret"""
        user_data = {"sub": "testuser"}
        token = create_access_token(user_data)
        
        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(token, "wrong_secret", algorithms=[settings.algorithm])
    
    def test_token_expired(self):
        """Test expired token"""
        user_data = {"sub": "testuser"}
        # Create token that expires immediately
        token = create_access_token(user_data, timedelta(seconds=-1))
        
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])