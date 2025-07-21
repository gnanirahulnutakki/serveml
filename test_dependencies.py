#!/usr/bin/env python3
"""
Test script to verify updated dependencies work correctly
"""

def test_imports():
    """Test that all major dependencies can be imported"""
    print("Testing dependency imports...")
    
    try:
        # Core dependencies
        import fastapi
        print(f"✓ FastAPI {fastapi.__version__}")
        
        import uvicorn
        print(f"✓ Uvicorn imported successfully")
        
        import pydantic
        print(f"✓ Pydantic {pydantic.__version__}")
        
        import numpy as np
        print(f"✓ NumPy {np.__version__}")
        
        import jinja2
        print(f"✓ Jinja2 {jinja2.__version__}")
        
        import boto3
        print(f"✓ Boto3 {boto3.__version__}")
        
        import sklearn
        print(f"✓ Scikit-learn {sklearn.__version__}")
        
        # Test dependencies
        import pytest
        print(f"✓ Pytest {pytest.__version__}")
        
        import httpx
        print(f"✓ HTTPX {httpx.__version__}")
        
        import requests
        print(f"✓ Requests {requests.__version__}")
        
        print("\nAll dependencies imported successfully!")
        return True
        
    except ImportError as e:
        print(f"\n✗ Import error: {e}")
        return False


def test_basic_functionality():
    """Test basic functionality with updated packages"""
    print("\nTesting basic functionality...")
    
    try:
        # Test NumPy
        arr = np.array([1, 2, 3, 4, 5])
        print(f"✓ NumPy array creation: {arr}")
        
        # Test Jinja2
        from jinja2 import Template
        template = Template("Hello {{ name }}!")
        result = template.render(name="ServeML")
        print(f"✓ Jinja2 template rendering: {result}")
        
        # Test Pydantic
        from pydantic import BaseModel
        
        class TestModel(BaseModel):
            name: str
            value: int
        
        model = TestModel(name="test", value=42)
        print(f"✓ Pydantic model creation: {model.model_dump()}")
        
        # Test FastAPI app creation
        from fastapi import FastAPI
        app = FastAPI()
        print("✓ FastAPI app created successfully")
        
        print("\nAll functionality tests passed!")
        return True
        
    except Exception as e:
        print(f"\n✗ Functionality error: {e}")
        return False


if __name__ == "__main__":
    print("ServeML Dependency Test\n" + "="*30)
    
    import_success = test_imports()
    functionality_success = test_basic_functionality()
    
    if import_success and functionality_success:
        print("\n✅ All tests passed! Dependencies are working correctly.")
        exit(0)
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        exit(1)