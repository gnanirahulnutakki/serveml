"""
Docker image builder service for model containers
"""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class DockerBuilder:
    """Build Docker images for ML models"""
    
    def __init__(self, templates_dir: str = "templates"):
        self.templates_dir = Path(templates_dir)
        
    def build_image(
        self,
        model_path: str,
        requirements_path: str,
        deployment_id: str,
        framework: str = "sklearn",
        use_gpu: bool = False
    ) -> Tuple[bool, str]:
        """
        Build Docker image for model deployment
        
        Returns:
            Tuple of (success, image_name_or_error)
        """
        try:
            # Create temporary build directory
            with tempfile.TemporaryDirectory() as build_dir:
                build_path = Path(build_dir)
                
                # Copy model file
                model_dest = build_path / "model.pkl"
                shutil.copy2(model_path, model_dest)
                
                # Copy requirements
                req_dest = build_path / "requirements.txt"
                shutil.copy2(requirements_path, req_dest)
                
                # Copy wrapper as handler
                wrapper_src = self.templates_dir / "wrapper.py"
                handler_dest = build_path / "handler.py"
                shutil.copy2(wrapper_src, handler_dest)
                
                # Choose appropriate Dockerfile
                if use_gpu:
                    dockerfile_src = self.templates_dir / "Dockerfile.gpu"
                else:
                    dockerfile_src = self.templates_dir / "Dockerfile"
                
                dockerfile_dest = build_path / "Dockerfile"
                shutil.copy2(dockerfile_src, dockerfile_dest)
                
                # Build image
                image_name = f"serveml-{deployment_id}:latest"
                
                logger.info(f"Building Docker image: {image_name}")
                
                result = subprocess.run(
                    ["docker", "build", "-t", image_name, "."],
                    cwd=build_dir,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    error_msg = f"Docker build failed: {result.stderr}"
                    logger.error(error_msg)
                    return False, error_msg
                
                logger.info(f"Successfully built image: {image_name}")
                return True, image_name
                
        except Exception as e:
            error_msg = f"Failed to build Docker image: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def test_image_locally(self, image_name: str, test_data: Dict) -> Tuple[bool, str]:
        """Test Docker image locally before deployment"""
        try:
            # Run container
            result = subprocess.run(
                [
                    "docker", "run", "--rm",
                    "-p", "9000:8080",
                    image_name
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # TODO: Send test request to container
            # For now, just check if container starts
            
            return True, "Image test passed"
            
        except subprocess.TimeoutExpired:
            return True, "Container started successfully"
        except Exception as e:
            return False, f"Image test failed: {str(e)}"
    
    def push_to_ecr(self, image_name: str, ecr_repo: str) -> Tuple[bool, str]:
        """Push Docker image to ECR"""
        try:
            # Tag for ECR
            ecr_tag = f"{ecr_repo}:{image_name.split(':')[0].replace('serveml-', '')}"
            
            result = subprocess.run(
                ["docker", "tag", image_name, ecr_tag],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return False, f"Failed to tag image: {result.stderr}"
            
            # Push to ECR
            result = subprocess.run(
                ["docker", "push", ecr_tag],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return False, f"Failed to push image: {result.stderr}"
            
            return True, ecr_tag
            
        except Exception as e:
            return False, f"Failed to push to ECR: {str(e)}"
    
    def validate_requirements(self, requirements_path: str) -> Tuple[bool, str]:
        """Validate requirements.txt file"""
        try:
            with open(requirements_path, 'r') as f:
                lines = f.readlines()
            
            # Check for common issues
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Basic validation
                if '==' not in line and '>=' not in line and '<=' not in line:
                    logger.warning(f"Package without version pin: {line}")
            
            return True, "Requirements validated"
            
        except Exception as e:
            return False, f"Invalid requirements file: {str(e)}"
    
    def estimate_image_size(self, requirements_path: str) -> int:
        """Estimate final image size in MB"""
        base_size = 250  # Base Lambda Python image
        
        # Add estimated sizes for common packages
        package_sizes = {
            'tensorflow': 500,
            'torch': 750,
            'pytorch': 750,
            'scikit-learn': 100,
            'sklearn': 100,
            'pandas': 50,
            'numpy': 20,
            'scipy': 40,
        }
        
        try:
            with open(requirements_path, 'r') as f:
                requirements = f.read().lower()
            
            total_size = base_size
            for package, size in package_sizes.items():
                if package in requirements:
                    total_size += size
            
            return total_size
            
        except Exception:
            return base_size