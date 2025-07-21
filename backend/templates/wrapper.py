"""
Universal ML Model Serving Wrapper for AWS Lambda
Supports scikit-learn, PyTorch, TensorFlow models
"""
import os
import json
import pickle
import logging
import traceback
from typing import Any, Dict, List, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Model cache for warm starts
MODEL_CACHE = {}

def load_model(model_path: str = None) -> Any:
    """Load ML model with caching support"""
    if model_path is None:
        model_path = os.environ.get('MODEL_PATH', '/opt/ml/model.pkl')
    
    # Check cache first
    if model_path in MODEL_CACHE:
        logger.info(f"Using cached model from {model_path}")
        return MODEL_CACHE[model_path]
    
    logger.info(f"Loading model from {model_path}")
    
    try:
        # Detect model type and load accordingly
        if model_path.endswith('.pkl'):
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
        elif model_path.endswith('.pt') or model_path.endswith('.pth'):
            import torch
            model = torch.load(model_path, map_location='cpu')
            model.eval()
        elif model_path.endswith('.h5') or model_path.endswith('.keras'):
            import tensorflow as tf
            model = tf.keras.models.load_model(model_path)
        else:
            raise ValueError(f"Unsupported model format: {model_path}")
        
        # Cache the model
        MODEL_CACHE[model_path] = model
        logger.info(f"Model loaded successfully: {type(model).__name__}")
        return model
        
    except Exception as e:
        logger.error(f"Failed to load model: {str(e)}")
        raise


def preprocess_input(data: Union[List, Dict], model_type: str) -> Any:
    """Preprocess input data based on model type"""
    try:
        if model_type == 'sklearn':
            # Scikit-learn expects list of lists
            if isinstance(data, dict):
                # Convert dict to list maintaining order
                return [list(data.values())]
            elif isinstance(data, list) and len(data) > 0:
                if isinstance(data[0], (int, float)):
                    return [data]
                return data
            return data
            
        elif model_type == 'pytorch':
            import torch
            import numpy as np
            # PyTorch expects tensors
            if isinstance(data, dict):
                data = list(data.values())
            tensor_data = torch.FloatTensor(data)
            if len(tensor_data.shape) == 1:
                tensor_data = tensor_data.unsqueeze(0)
            return tensor_data
            
        elif model_type == 'tensorflow':
            import numpy as np
            # TensorFlow expects numpy arrays
            if isinstance(data, dict):
                data = list(data.values())
            return np.array([data]) if isinstance(data[0], (int, float)) else np.array(data)
            
        return data
        
    except Exception as e:
        logger.error(f"Preprocessing failed: {str(e)}")
        raise


def postprocess_output(output: Any, model_type: str) -> Union[List, Dict]:
    """Postprocess model output to JSON-serializable format"""
    try:
        if model_type == 'sklearn':
            # Handle numpy arrays
            if hasattr(output, 'tolist'):
                return output.tolist()
            return output
            
        elif model_type == 'pytorch':
            # Handle PyTorch tensors
            if hasattr(output, 'detach'):
                return output.detach().cpu().numpy().tolist()
            return output
            
        elif model_type == 'tensorflow':
            # Handle TensorFlow tensors
            if hasattr(output, 'numpy'):
                return output.numpy().tolist()
            return output
            
        return output
        
    except Exception as e:
        logger.error(f"Postprocessing failed: {str(e)}")
        raise


def detect_model_type(model: Any) -> str:
    """Detect the type of ML framework"""
    model_class = str(type(model))
    
    if 'sklearn' in model_class or 'scikit' in model_class:
        return 'sklearn'
    elif 'torch' in model_class or 'pytorch' in model_class:
        return 'pytorch'
    elif 'tensorflow' in model_class or 'keras' in model_class:
        return 'tensorflow'
    else:
        # Default to sklearn for unknown types
        return 'sklearn'


def lambda_handler(event: Dict, context: Any) -> Dict:
    """AWS Lambda handler function"""
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # Parse request body
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event
        
        # Extract input data
        input_data = body.get('data', body.get('input', body))
        
        # Load model
        model = load_model()
        model_type = detect_model_type(model)
        logger.info(f"Model type detected: {model_type}")
        
        # Preprocess input
        processed_input = preprocess_input(input_data, model_type)
        
        # Make prediction
        if hasattr(model, 'predict'):
            prediction = model.predict(processed_input)
        elif hasattr(model, 'forward'):
            # PyTorch model
            prediction = model(processed_input)
        else:
            # TensorFlow/Keras model
            prediction = model(processed_input)
        
        # Postprocess output
        output = postprocess_output(prediction, model_type)
        
        # Prepare response
        response = {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'prediction': output,
                'model_type': model_type,
                'model_class': type(model).__name__,
                'input_shape': str(processed_input.shape) if hasattr(processed_input, 'shape') else str(len(processed_input))
            })
        }
        
        logger.info(f"Prediction successful: {output}")
        return response
        
    except Exception as e:
        logger.error(f"Prediction failed: {str(e)}")
        logger.error(traceback.format_exc())
        
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e),
                'type': type(e).__name__
            })
        }


def health_check() -> Dict:
    """Health check endpoint"""
    try:
        model = load_model()
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'status': 'healthy',
                'model_loaded': model is not None,
                'model_type': detect_model_type(model) if model else None
            })
        }
    except Exception as e:
        return {
            'statusCode': 503,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'status': 'unhealthy',
                'error': str(e)
            })
        }


# For local testing
if __name__ == "__main__":
    # Test event
    test_event = {
        'body': json.dumps({
            'data': [5.1, 3.5, 1.4, 0.2]  # Iris dataset sample
        })
    }
    
    # Test handler
    response = lambda_handler(test_event, None)
    print(json.dumps(response, indent=2))