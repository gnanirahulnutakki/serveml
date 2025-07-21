"""
Tests for model validator service
"""
import pytest
import tempfile
import pickle
import os
from services.model_validator import ModelValidator
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import load_iris


class TestModelValidator:
    
    @pytest.fixture
    def sklearn_model_path(self):
        """Create a test sklearn model"""
        with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as f:
            # Train a simple model
            X, y = load_iris(return_X_y=True)
            model = RandomForestClassifier(n_estimators=10, random_state=42)
            model.fit(X, y)
            
            # Save model
            pickle.dump(model, f)
            return f.name
    
    @pytest.fixture
    def requirements_path(self):
        """Create a test requirements file"""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False, mode='w') as f:
            f.write("scikit-learn==1.3.0\n")
            f.write("numpy==1.24.3\n")
            f.write("pandas>=1.5.0\n")
            return f.name
    
    def test_validate_sklearn_model_success(self, sklearn_model_path):
        """Test validation of a valid sklearn model"""
        is_valid, metadata = ModelValidator.validate_model(sklearn_model_path)
        
        assert is_valid is True
        assert metadata['framework'] == 'sklearn'
        assert metadata['model_type'] == 'RandomForestClassifier (Classifier)'
        assert metadata['input_shape'] == (4,)  # Iris features
        assert len(metadata['errors']) == 0
        
        # Cleanup
        os.unlink(sklearn_model_path)
    
    def test_validate_invalid_model_file(self):
        """Test validation of non-existent model file"""
        is_valid, metadata = ModelValidator.validate_model("nonexistent.pkl")
        
        assert is_valid is False
        assert len(metadata['errors']) > 0
    
    def test_validate_requirements_success(self, requirements_path):
        """Test validation of valid requirements file"""
        is_valid, metadata = ModelValidator.validate_requirements(requirements_path)
        
        assert is_valid is True
        assert len(metadata['packages']) == 3
        assert metadata['packages'][0]['name'] == 'scikit-learn'
        assert metadata['packages'][0]['version'] == '1.3.0'
        
        # Cleanup
        os.unlink(requirements_path)
    
    def test_validate_requirements_with_warnings(self):
        """Test requirements validation with version ranges"""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False, mode='w') as f:
            f.write("numpy\n")  # No version
            f.write("pandas>=1.5.0\n")  # Version range
            req_path = f.name
        
        is_valid, metadata = ModelValidator.validate_requirements(req_path)
        
        assert is_valid is True
        assert len(metadata['warnings']) == 2
        
        # Cleanup
        os.unlink(req_path)
    
    def test_generate_test_payload(self):
        """Test generation of test payload"""
        metadata = {'input_shape': (4,)}
        payload = ModelValidator.generate_test_payload(metadata)
        
        assert 'data' in payload
        assert len(payload['data']) == 4
        
    def test_model_size_limit(self):
        """Test model size validation"""
        # Create a large file
        with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as f:
            # Write 600MB of data (over the 500MB limit)
            f.write(b'0' * (600 * 1024 * 1024))
            large_model_path = f.name
        
        is_valid, metadata = ModelValidator.validate_model(large_model_path)
        
        assert is_valid is False
        assert 'Model too large' in str(metadata['errors'])
        
        # Cleanup
        os.unlink(large_model_path)