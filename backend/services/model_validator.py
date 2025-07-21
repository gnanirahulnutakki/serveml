"""
Model validation service to ensure models are deployable
"""
import pickle
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import logging
import numpy as np

logger = logging.getLogger(__name__)


class ModelValidator:
    """Validate ML models before deployment"""
    
    @staticmethod
    def validate_model(model_path: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate a model file
        
        Returns:
            Tuple of (is_valid, metadata)
        """
        metadata = {
            'framework': None,
            'model_type': None,
            'input_shape': None,
            'output_shape': None,
            'size_mb': 0,
            'errors': []
        }
        
        try:
            # Check file size
            file_size = Path(model_path).stat().st_size
            metadata['size_mb'] = file_size / (1024 * 1024)
            
            if metadata['size_mb'] > 500:
                metadata['errors'].append(f"Model too large: {metadata['size_mb']:.1f}MB (max 500MB)")
                return False, metadata
            
            # Try to load the model
            if model_path.endswith('.pkl'):
                return ModelValidator._validate_sklearn_model(model_path, metadata)
            elif model_path.endswith(('.pt', '.pth')):
                return ModelValidator._validate_pytorch_model(model_path, metadata)
            elif model_path.endswith(('.h5', '.keras')):
                return ModelValidator._validate_tensorflow_model(model_path, metadata)
            else:
                metadata['errors'].append(f"Unsupported model format: {Path(model_path).suffix}")
                return False, metadata
                
        except Exception as e:
            metadata['errors'].append(f"Validation error: {str(e)}")
            return False, metadata
    
    @staticmethod
    def _validate_sklearn_model(model_path: str, metadata: Dict) -> Tuple[bool, Dict]:
        """Validate scikit-learn model"""
        try:
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
            
            metadata['framework'] = 'sklearn'
            metadata['model_type'] = type(model).__name__
            
            # Check if model has required methods
            if not hasattr(model, 'predict'):
                metadata['errors'].append("Model missing 'predict' method")
                return False, metadata
            
            # Try to get feature information
            if hasattr(model, 'n_features_in_'):
                metadata['input_shape'] = (model.n_features_in_,)
            elif hasattr(model, 'n_features_'):
                metadata['input_shape'] = (model.n_features_,)
            
            # Test with dummy data
            try:
                if metadata['input_shape']:
                    X_test = np.random.randn(1, metadata['input_shape'][0])
                else:
                    # Try common input sizes
                    for n_features in [4, 10, 20, 100]:
                        try:
                            X_test = np.random.randn(1, n_features)
                            output = model.predict(X_test)
                            metadata['input_shape'] = (n_features,)
                            break
                        except:
                            continue
                
                if metadata['input_shape']:
                    output = model.predict(X_test)
                    metadata['output_shape'] = output.shape[1:] if len(output.shape) > 1 else (1,)
                    
                    # Check if classifier
                    if hasattr(model, 'predict_proba'):
                        metadata['model_type'] += ' (Classifier)'
                    elif hasattr(model, 'score'):
                        metadata['model_type'] += ' (Regressor)'
                
            except Exception as e:
                logger.warning(f"Could not test model predictions: {e}")
            
            return True, metadata
            
        except Exception as e:
            metadata['errors'].append(f"Failed to load sklearn model: {str(e)}")
            return False, metadata
    
    @staticmethod
    def _validate_pytorch_model(model_path: str, metadata: Dict) -> Tuple[bool, Dict]:
        """Validate PyTorch model"""
        try:
            import torch
            
            # Load model
            model = torch.load(model_path, map_location='cpu')
            
            metadata['framework'] = 'pytorch'
            metadata['model_type'] = type(model).__name__
            
            # Check if it's a state dict or full model
            if isinstance(model, dict):
                metadata['errors'].append("Model is a state dict, not a full model. Please save the entire model.")
                return False, metadata
            
            # Set to eval mode
            model.eval()
            
            # Try to infer input shape
            # This is tricky with PyTorch, so we'll try common sizes
            test_passed = False
            for batch_size in [1]:
                for input_size in [(3, 224, 224), (1, 28, 28), (10,), (100,), (784,)]:
                    try:
                        if len(input_size) == 1:
                            x = torch.randn(batch_size, input_size[0])
                        elif len(input_size) == 3:
                            x = torch.randn(batch_size, *input_size)
                        else:
                            x = torch.randn(batch_size, *input_size)
                        
                        with torch.no_grad():
                            output = model(x)
                        
                        metadata['input_shape'] = input_size
                        metadata['output_shape'] = tuple(output.shape[1:])
                        test_passed = True
                        break
                        
                    except:
                        continue
                
                if test_passed:
                    break
            
            if not test_passed:
                metadata['errors'].append("Could not determine model input shape. Please ensure model accepts standard tensor inputs.")
                return False, metadata
            
            return True, metadata
            
        except ImportError:
            metadata['errors'].append("PyTorch not installed. Cannot validate .pt/.pth files.")
            return False, metadata
        except Exception as e:
            metadata['errors'].append(f"Failed to load PyTorch model: {str(e)}")
            return False, metadata
    
    @staticmethod
    def _validate_tensorflow_model(model_path: str, metadata: Dict) -> Tuple[bool, Dict]:
        """Validate TensorFlow/Keras model"""
        try:
            import tensorflow as tf
            
            # Load model
            model = tf.keras.models.load_model(model_path)
            
            metadata['framework'] = 'tensorflow'
            metadata['model_type'] = model.__class__.__name__
            
            # Get input/output shapes
            if hasattr(model, 'input_shape'):
                metadata['input_shape'] = model.input_shape[1:]  # Remove batch dimension
            
            if hasattr(model, 'output_shape'):
                metadata['output_shape'] = model.output_shape[1:]  # Remove batch dimension
            
            # Get model summary
            if hasattr(model, 'count_params'):
                metadata['total_params'] = model.count_params()
            
            return True, metadata
            
        except ImportError:
            metadata['errors'].append("TensorFlow not installed. Cannot validate .h5/.keras files.")
            return False, metadata
        except Exception as e:
            metadata['errors'].append(f"Failed to load TensorFlow model: {str(e)}")
            return False, metadata
    
    @staticmethod
    def generate_test_payload(metadata: Dict) -> Dict[str, Any]:
        """Generate a test payload based on model metadata"""
        if not metadata.get('input_shape'):
            return {'data': [1.0] * 10}  # Default fallback
        
        input_shape = metadata['input_shape']
        
        if len(input_shape) == 1:
            # 1D input (typical for sklearn)
            return {'data': [0.5] * input_shape[0]}
        elif len(input_shape) == 3:
            # Image input (typical for CNN)
            return {'data': np.random.rand(*input_shape).tolist()}
        else:
            # Other shapes
            return {'data': np.random.rand(*input_shape).tolist()}
    
    @staticmethod
    def validate_requirements(requirements_path: str) -> Tuple[bool, Dict[str, Any]]:
        """Validate requirements.txt file"""
        metadata = {
            'packages': [],
            'warnings': [],
            'errors': []
        }
        
        try:
            with open(requirements_path, 'r') as f:
                lines = f.readlines()
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Parse package info
                if '==' in line:
                    package, version = line.split('==')
                    metadata['packages'].append({'name': package, 'version': version})
                elif '>=' in line or '<=' in line or '>' in line or '<' in line:
                    metadata['warnings'].append(f"Package with version range: {line}")
                    metadata['packages'].append({'name': line.split()[0], 'version': 'range'})
                else:
                    metadata['warnings'].append(f"Package without version: {line}")
                    metadata['packages'].append({'name': line, 'version': 'latest'})
            
            # Check for conflicting packages
            package_names = [p['name'].lower() for p in metadata['packages']]
            if 'tensorflow' in package_names and 'tensorflow-gpu' in package_names:
                metadata['errors'].append("Both tensorflow and tensorflow-gpu specified")
            
            return len(metadata['errors']) == 0, metadata
            
        except Exception as e:
            metadata['errors'].append(f"Failed to parse requirements: {str(e)}")
            return False, metadata