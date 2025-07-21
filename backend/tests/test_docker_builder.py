"""
Tests for Docker builder service
"""
import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from services.docker_builder import DockerBuilder


class TestDockerBuilder:
    
    @pytest.fixture
    def docker_builder(self):
        """Create DockerBuilder instance"""
        return DockerBuilder(templates_dir="../templates")
    
    @pytest.fixture
    def model_path(self):
        """Create a test model file"""
        with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as f:
            f.write(b'test model content')
            return f.name
    
    @pytest.fixture
    def requirements_path(self):
        """Create a test requirements file"""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False, mode='w') as f:
            f.write("scikit-learn==1.3.0\n")
            f.write("numpy==1.24.3\n")
            return f.name
    
    def test_validate_requirements_success(self, docker_builder, requirements_path):
        """Test requirements validation"""
        is_valid, result = docker_builder.validate_requirements(requirements_path)
        
        assert is_valid is True
        assert result == "Requirements validated"
        
        # Cleanup
        os.unlink(requirements_path)
    
    def test_validate_requirements_empty_file(self, docker_builder):
        """Test validation of empty requirements file"""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False, mode='w') as f:
            empty_path = f.name
        
        is_valid, result = docker_builder.validate_requirements(empty_path)
        
        assert is_valid is True  # Empty file is technically valid
        
        # Cleanup
        os.unlink(empty_path)
    
    def test_estimate_image_size(self, docker_builder):
        """Test Docker image size estimation"""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False, mode='w') as f:
            f.write("tensorflow==2.15.0\n")
            f.write("numpy==1.24.3\n")
            f.write("pandas==2.0.3\n")
            req_path = f.name
        
        size_mb = docker_builder.estimate_image_size(req_path)
        
        # Base (250) + TensorFlow (500) + numpy (20) + pandas (50) = 820
        assert size_mb == 820
        
        # Cleanup
        os.unlink(req_path)
    
    @patch('subprocess.run')
    def test_build_image_success(self, mock_run, docker_builder, model_path, requirements_path):
        """Test successful Docker image build"""
        # Mock successful docker build
        mock_run.return_value = Mock(returncode=0, stdout='', stderr='')
        
        # Create a mock templates directory
        os.makedirs("templates", exist_ok=True)
        with open("templates/wrapper.py", "w") as f:
            f.write("# Mock wrapper")
        with open("templates/Dockerfile", "w") as f:
            f.write("FROM python:3.11")
        
        success, result = docker_builder.build_image(
            model_path=model_path,
            requirements_path=requirements_path,
            deployment_id="test-123",
            framework="sklearn"
        )
        
        assert success is True
        assert result == "serveml-test-123:latest"
        
        # Cleanup
        os.unlink(model_path)
        os.unlink(requirements_path)
        os.unlink("templates/wrapper.py")
        os.unlink("templates/Dockerfile")
        os.rmdir("templates")
    
    @patch('subprocess.run')
    def test_build_image_failure(self, mock_run, docker_builder, model_path, requirements_path):
        """Test failed Docker image build"""
        # Mock failed docker build
        mock_run.return_value = Mock(returncode=1, stdout='', stderr='Docker build error')
        
        # Create a mock templates directory
        os.makedirs("templates", exist_ok=True)
        with open("templates/wrapper.py", "w") as f:
            f.write("# Mock wrapper")
        with open("templates/Dockerfile", "w") as f:
            f.write("FROM python:3.11")
        
        success, result = docker_builder.build_image(
            model_path=model_path,
            requirements_path=requirements_path,
            deployment_id="test-123",
            framework="sklearn"
        )
        
        assert success is False
        assert "Docker build failed" in result
        
        # Cleanup
        os.unlink(model_path)
        os.unlink(requirements_path)
        os.unlink("templates/wrapper.py")
        os.unlink("templates/Dockerfile")
        os.rmdir("templates")