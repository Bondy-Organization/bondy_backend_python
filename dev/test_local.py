#!/usr/bin/env python3

import requests
import time

# Test local server
print("Testing local server...")

try:
    # Test /
    print("Testing /...")
    response = requests.get("http://localhost:8083/", timeout=5)
    print(f"Status: {response.status_code}")
    print(f"Content: {response.text}")
    print()
    
    # Test /health  
    print("Testing /health...") 
    response = requests.get("http://localhost:8083/health", timeout=5)
    print(f"Status: {response.status_code}")
    print(f"Content: {response.text}")
    print()
    
except requests.exceptions.RequestException as e:
    print(f"Error: {e}")

# Test remote server
print("Testing remote server...")

try:
    # Test /
    print("Testing /...")
    response = requests.get("https://bondy-backend-python-mi3a.onrender.com/", timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Content: {response.text}")
    print()
     
    # Test /health  
    print("Testing /health...")
    response = requests.get("https://bondy-backend-python-mi3a.onrender.com/health", timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Content: {response.text}")
    print()
    
except requests.exceptions.RequestException as e:
    print(f"Error: {e}")
