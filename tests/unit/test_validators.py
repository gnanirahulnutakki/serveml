"""
Unit tests for validators
"""
import pytest
import tempfile
import pickle
from pathlib import Path
from validators import validate_model_file, validate_requirements_file


class TestValidators:
    """Test validation functions"""
    
    def test_validate_sklearn_model(self):
        """Test scikit-learn model validation"""
        from sklearn.ensemble import RandomForestClassifier
        
        # Create valid model
        model = RandomForestClassifier()
        
        with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as f:
            pickle.dump(model, f)
            temp_path = f.name
        
        try:
            result = validate_model_file(temp_path)
            assert result["valid"] is True
            assert result["framework"] == "sklearn"
            assert result["model_type"] == "RandomForestClassifier"
        finally:
            Path(temp_path).unlink()
    
    def test_validate_invalid_pickle(self):
        """Test invalid pickle file"""
        with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as f:
            f.write(b"not a valid pickle")
            temp_path = f.name
        
        try:
            result = validate_model_file(temp_path)
            assert result["valid"] is False
            assert "error" in result
        finally:
            Path(temp_path).unlink()
    
    def test_validate_requirements_valid(self):
        """Test valid requirements file"""
        requirements = """numpy==1.24.3
scikit-learn>=1.0.0
pandas>2.0
matplotlib~=3.7.0"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(requirements)
            temp_path = f.name
        
        try:
            result = validate_requirements_file(temp_path)
            assert result["valid"] is True
            assert len(result["packages"]) == 4
            assert "numpy==1.24.3" in result["packages"]
        finally:
            Path(temp_path).unlink()
    
    def test_validate_requirements_invalid(self):
        """Test invalid requirements file"""
        requirements = """numpy==1.24.3
invalid package name
this-is-not-valid==
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(requirements)
            temp_path = f.name
        
        try:
            result = validate_requirements_file(temp_path)
            assert result["valid"] is False
            assert len(result["errors"]) > 0
        finally:
            Path(temp_path).unlink()
    
    def test_validate_requirements_with_comments(self):
        """Test requirements file with comments"""
        requirements = """# Core dependencies
numpy==1.24.3  # For numerical operations
scikit-learn>=1.0.0

# Visualization
matplotlib~=3.7.0
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(requirements)
            temp_path = f.name
        
        try:
            result = validate_requirements_file(temp_path)
            assert result["valid"] is True
            assert len(result["packages"]) == 3  # Comments should be ignored
        finally:
            Path(temp_path).unlink()
    
    def test_validate_pytorch_model(self):
        """Test PyTorch model validation"""
        try:
            import torch
            import torch.nn as nn
            
            class SimpleModel(nn.Module):
                def __init__(self):
                    super().__init__()
                    self.linear = nn.Linear(10, 1)
                
                def forward(self, x):
                    return self.linear(x)
            
            model = SimpleModel()
            
            with tempfile.NamedTemporaryFile(suffix='.pt', delete=False) as f:
                torch.save(model, f.name)
                temp_path = f.name
            
            try:
                result = validate_model_file(temp_path)
                assert result["valid"] is True
                assert result["framework"] == "pytorch"
            finally:
                Path(temp_path).unlink()
                
        except ImportError:
            pytest.skip("PyTorch not installed")
    
    def test_validate_tensorflow_model(self):
        """Test TensorFlow model validation"""
        try:
            import tensorflow as tf
            
            model = tf.keras.Sequential([
                tf.keras.layers.Dense(10, activation='relu', input_shape=(5,)),
                tf.keras.layers.Dense(1)
            ])
            
            with tempfile.TemporaryDirectory() as temp_dir:
                model_path = Path(temp_dir) / "model.h5"
                model.save(model_path)
                
                result = validate_model_file(str(model_path))
                assert result["valid"] is True
                assert result["framework"] == "tensorflow"
                
        except ImportError:
            pytest.skip("TensorFlow not installed")