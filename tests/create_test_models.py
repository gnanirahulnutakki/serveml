#!/usr/bin/env python3
"""
Create various test models for ServeML testing
"""
import os
import pickle
import json
import numpy as np
from pathlib import Path

# Create test models directory
test_models_dir = Path("test_models")
test_models_dir.mkdir(exist_ok=True)


def create_sklearn_models():
    """Create various scikit-learn models"""
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
    from sklearn.linear_model import LogisticRegression, LinearRegression
    from sklearn.svm import SVC
    from sklearn.datasets import load_iris, load_digits, load_diabetes
    import joblib
    
    print("Creating scikit-learn models...")
    
    # 1. Small classification model (Iris dataset)
    X_iris, y_iris = load_iris(return_X_y=True)
    
    # Logistic Regression (tiny model ~5KB)
    lr_model = LogisticRegression(max_iter=200)
    lr_model.fit(X_iris, y_iris)
    with open(test_models_dir / "iris_logistic.pkl", "wb") as f:
        pickle.dump(lr_model, f)
    
    # Random Forest (small model ~50KB)
    rf_model = RandomForestClassifier(n_estimators=10, random_state=42)
    rf_model.fit(X_iris, y_iris)
    joblib.dump(rf_model, test_models_dir / "iris_rf.pkl")
    
    # 2. Medium classification model (Digits dataset)
    X_digits, y_digits = load_digits(return_X_y=True)
    
    # SVM (medium model ~500KB)
    svm_model = SVC(kernel='rbf', probability=True)
    svm_model.fit(X_digits[:500], y_digits[:500])  # Subset for faster training
    joblib.dump(svm_model, test_models_dir / "digits_svm.pkl")
    
    # 3. Regression model (Diabetes dataset)
    X_diabetes, y_diabetes = load_diabetes(return_X_y=True)
    
    # Linear Regression (tiny model)
    lr_reg = LinearRegression()
    lr_reg.fit(X_diabetes, y_diabetes)
    with open(test_models_dir / "diabetes_linear.pkl", "wb") as f:
        pickle.dump(lr_reg, f)
    
    # Gradient Boosting (larger model ~1MB)
    gb_model = GradientBoostingRegressor(n_estimators=100, random_state=42)
    gb_model.fit(X_diabetes, y_diabetes)
    joblib.dump(gb_model, test_models_dir / "diabetes_gb.pkl", compress=3)
    
    print("✓ Created 5 scikit-learn models")


def create_pytorch_models():
    """Create PyTorch models"""
    try:
        import torch
        import torch.nn as nn
        
        print("Creating PyTorch models...")
        
        # 1. Simple feedforward network
        class SimpleNet(nn.Module):
            def __init__(self, input_size=4, hidden_size=10, output_size=3):
                super().__init__()
                self.fc1 = nn.Linear(input_size, hidden_size)
                self.relu = nn.ReLU()
                self.fc2 = nn.Linear(hidden_size, output_size)
                
            def forward(self, x):
                x = self.fc1(x)
                x = self.relu(x)
                x = self.fc2(x)
                return x
        
        # Small model for Iris
        simple_model = SimpleNet(4, 10, 3)
        torch.save(simple_model, test_models_dir / "iris_torch.pt")
        
        # 2. Convolutional network (for image data)
        class SimpleCNN(nn.Module):
            def __init__(self):
                super().__init__()
                self.conv1 = nn.Conv2d(1, 16, kernel_size=3)
                self.pool = nn.MaxPool2d(2)
                self.conv2 = nn.Conv2d(16, 32, kernel_size=3)
                self.fc1 = nn.Linear(32 * 5 * 5, 10)
                
            def forward(self, x):
                x = self.pool(torch.relu(self.conv1(x)))
                x = self.pool(torch.relu(self.conv2(x)))
                x = x.view(-1, 32 * 5 * 5)
                x = self.fc1(x)
                return x
        
        cnn_model = SimpleCNN()
        torch.save(cnn_model.state_dict(), test_models_dir / "mnist_cnn.pth")
        
        print("✓ Created 2 PyTorch models")
        
    except ImportError:
        print("⚠️  PyTorch not installed, skipping PyTorch models")


def create_tensorflow_models():
    """Create TensorFlow/Keras models"""
    try:
        import tensorflow as tf
        
        print("Creating TensorFlow models...")
        
        # 1. Simple sequential model for Iris
        iris_model = tf.keras.Sequential([
            tf.keras.layers.Dense(10, activation='relu', input_shape=(4,)),
            tf.keras.layers.Dense(10, activation='relu'),
            tf.keras.layers.Dense(3, activation='softmax')
        ])
        iris_model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
        iris_model.save(test_models_dir / "iris_tf.h5")
        
        # 2. CNN for MNIST-like data
        cnn_model = tf.keras.Sequential([
            tf.keras.layers.Conv2D(32, (3, 3), activation='relu', input_shape=(28, 28, 1)),
            tf.keras.layers.MaxPooling2D((2, 2)),
            tf.keras.layers.Conv2D(64, (3, 3), activation='relu'),
            tf.keras.layers.MaxPooling2D((2, 2)),
            tf.keras.layers.Flatten(),
            tf.keras.layers.Dense(64, activation='relu'),
            tf.keras.layers.Dense(10, activation='softmax')
        ])
        cnn_model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
        cnn_model.save(test_models_dir / "mnist_tf.keras")
        
        print("✓ Created 2 TensorFlow models")
        
    except ImportError:
        print("⚠️  TensorFlow not installed, skipping TensorFlow models")


def create_requirements_files():
    """Create various requirements.txt files for testing"""
    print("Creating requirements files...")
    
    requirements = {
        "minimal": "scikit-learn==1.3.0\nnumpy==1.24.3",
        
        "sklearn_full": """scikit-learn==1.3.0
numpy==1.24.3
scipy==1.11.1
pandas==2.0.3
joblib==1.3.0""",
        
        "pytorch": """torch==2.0.1
torchvision==0.15.2
numpy==1.24.3
pillow==10.0.0""",
        
        "tensorflow": """tensorflow==2.13.0
numpy==1.24.3
pillow==10.0.0
h5py==3.9.0""",
        
        "complex": """scikit-learn==1.3.0
pandas==2.0.3
numpy==1.24.3
scipy==1.11.1
matplotlib==3.7.2
seaborn==0.12.2
xgboost==1.7.6
lightgbm==4.0.0
plotly==5.15.0""",
        
        "pinned_versions": """scikit-learn==1.3.0
numpy==1.24.3
pandas==2.0.3
scipy==1.11.1
matplotlib==3.7.2
seaborn==0.12.2
requests==2.31.0
urllib3==2.0.4
certifi==2023.7.22""",
        
        "with_ranges": """scikit-learn>=1.0.0,<2.0.0
numpy>=1.20.0
pandas>2.0
scipy~=1.11.0
matplotlib!=3.7.0""",
        
        "invalid": """nonexistent-package==1.0.0
broken_requirement
scikit-learn==99.99.99
this-is-not-a-valid-package"""
    }
    
    for name, content in requirements.items():
        with open(test_models_dir / f"requirements_{name}.txt", "w") as f:
            f.write(content)
    
    print(f"✓ Created {len(requirements)} requirements files")


def create_test_payloads():
    """Create test prediction payloads"""
    print("Creating test payloads...")
    
    test_data_dir = Path("test_data")
    test_data_dir.mkdir(exist_ok=True)
    
    payloads = {
        # Iris dataset sample (4 features)
        "iris_single": {
            "data": [5.1, 3.5, 1.4, 0.2]
        },
        
        "iris_batch": {
            "data": [
                [5.1, 3.5, 1.4, 0.2],
                [4.9, 3.0, 1.4, 0.2],
                [6.2, 3.4, 5.4, 2.3]
            ]
        },
        
        # Digits dataset sample (64 features)
        "digits_single": {
            "data": np.random.rand(64).tolist()
        },
        
        # Diabetes dataset sample (10 features)
        "diabetes_single": {
            "data": np.random.rand(10).tolist()
        },
        
        # Image data (flattened 28x28)
        "mnist_single": {
            "data": np.random.rand(784).tolist()
        },
        
        # Large payload for stress testing
        "large_batch": {
            "data": np.random.rand(100, 100).tolist()
        },
        
        # Invalid payloads for error testing
        "invalid_empty": {},
        
        "invalid_type": {
            "data": "not a list"
        },
        
        "invalid_shape": {
            "data": [1, 2]  # Wrong number of features
        }
    }
    
    for name, payload in payloads.items():
        with open(test_data_dir / f"payload_{name}.json", "w") as f:
            json.dump(payload, f, indent=2)
    
    print(f"✓ Created {len(payloads)} test payloads")


def create_model_metadata():
    """Create metadata for test models"""
    print("Creating model metadata...")
    
    metadata = {
        "iris_logistic.pkl": {
            "framework": "sklearn",
            "model_type": "LogisticRegression",
            "input_shape": [4],
            "output_shape": [3],
            "size_kb": 5,
            "description": "Logistic regression trained on Iris dataset"
        },
        "iris_rf.pkl": {
            "framework": "sklearn",
            "model_type": "RandomForestClassifier",
            "input_shape": [4],
            "output_shape": [3],
            "size_kb": 50,
            "description": "Random forest trained on Iris dataset"
        },
        "digits_svm.pkl": {
            "framework": "sklearn",
            "model_type": "SVC",
            "input_shape": [64],
            "output_shape": [10],
            "size_kb": 500,
            "description": "SVM trained on digits dataset"
        },
        "iris_torch.pt": {
            "framework": "pytorch",
            "model_type": "SimpleNet",
            "input_shape": [4],
            "output_shape": [3],
            "size_kb": 10,
            "description": "Simple neural network for Iris classification"
        },
        "iris_tf.h5": {
            "framework": "tensorflow",
            "model_type": "Sequential",
            "input_shape": [4],
            "output_shape": [3],
            "size_kb": 50,
            "description": "Keras sequential model for Iris classification"
        }
    }
    
    with open(test_models_dir / "model_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    
    print("✓ Created model metadata")


def main():
    """Create all test artifacts"""
    print("Creating ServeML test artifacts...")
    print("-" * 50)
    
    create_sklearn_models()
    create_pytorch_models()
    create_tensorflow_models()
    create_requirements_files()
    create_test_payloads()
    create_model_metadata()
    
    print("-" * 50)
    print("✅ All test artifacts created successfully!")
    print(f"📁 Models saved in: {test_models_dir.absolute()}")
    print(f"📁 Test data saved in: test_data/")


if __name__ == "__main__":
    main()