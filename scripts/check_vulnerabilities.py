#!/usr/bin/env python3
"""
Script to check for known vulnerabilities in dependencies
Run this to identify which packages need security updates
"""

import subprocess
import sys

def check_with_pip_audit():
    """Use pip-audit to check for vulnerabilities"""
    print("Checking for vulnerabilities with pip-audit...")
    try:
        # Install pip-audit if not present
        subprocess.run([sys.executable, "-m", "pip", "install", "pip-audit"], 
                      capture_output=True)
        
        # Run pip-audit
        result = subprocess.run([sys.executable, "-m", "pip_audit", "-r", "backend/requirements.txt"],
                              capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)
    except Exception as e:
        print(f"pip-audit error: {e}")

def check_with_safety():
    """Use safety to check for vulnerabilities"""
    print("\nChecking for vulnerabilities with safety...")
    try:
        # Run safety check
        result = subprocess.run([sys.executable, "-m", "safety", "check", "-r", "backend/requirements.txt", "--json"],
                              capture_output=True, text=True)
        print(result.stdout)
    except Exception as e:
        print(f"safety error: {e}")

def list_all_dependencies():
    """List all installed dependencies with versions"""
    print("\nInstalled packages:")
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "list", "--format=freeze"],
                              capture_output=True, text=True)
        print(result.stdout)
    except Exception as e:
        print(f"pip list error: {e}")

if __name__ == "__main__":
    print("ServeML Vulnerability Check\n" + "="*40)
    
    # Try different vulnerability checkers
    check_with_pip_audit()
    check_with_safety()
    list_all_dependencies()
    
    print("\nNote: Check https://github.com/gnanirahulnutakki/serveml/security/dependabot for specific GitHub alerts")