#!/usr/bin/env python3
"""
Create a test model for ServeML development
This script creates a simple scikit-learn model and requirements.txt
"""

import pickle
import numpy as np
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import os

def create_test_model():
    """Create and save a test model"""
    print("Creating test model...")
    
    # Load iris dataset
    X, y = load_iris(return_X_y=True)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Train a simple model
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    model.fit(X_train, y_train)
    
    # Test accuracy
    accuracy = model.score(X_test, y_test)
    print(f"Model accuracy: {accuracy:.2f}")
    
    # Save model
    os.makedirs('test_models', exist_ok=True)
    model_path = 'test_models/iris_model.pkl'
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    print(f"Model saved to: {model_path}")
    
    # Create requirements.txt
    requirements_path = 'test_models/requirements.txt'
    with open(requirements_path, 'w') as f:
        f.write("""scikit-learn==1.3.0
numpy==1.24.3
scipy==1.11.1""")
    print(f"Requirements saved to: {requirements_path}")
    
    # Create sample prediction code
    sample_code = '''
# Sample prediction
import pickle
import numpy as np

# Load model
with open('iris_model.pkl', 'rb') as f:
    model = pickle.load(f)

# Make prediction
sample_data = [[5.1, 3.5, 1.4, 0.2]]  # Iris setosa example
prediction = model.predict(sample_data)
print(f"Predicted class: {prediction[0]}")

# Get probabilities
probabilities = model.predict_proba(sample_data)
print(f"Class probabilities: {probabilities[0]}")
'''
    
    sample_path = 'test_models/sample_prediction.py'
    with open(sample_path, 'w') as f:
        f.write(sample_code)
    print(f"Sample code saved to: {sample_path}")
    
    print("\nTest model created successfully!")
    print("You can now upload 'iris_model.pkl' and 'requirements.txt' to ServeML")

if __name__ == "__main__":
    create_test_model()