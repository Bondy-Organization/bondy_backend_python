#!/usr/bin/env python3

import requests
import time

# Test local server
print("Testing local server...")

if False:
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

remote_server = 'https://bondy-backend-python-mi3a.onrender.com/' if False else 'https://bondy-oru7l52q.b4a.run/'
try:
    # Test /
    print("Testing /...")
    response = requests.get(remote_server, timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Content: {response.text}")
    print()
     
    # Test /health  
    print("Testing /health...")
    response = requests.get(f"{remote_server}health", timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Content: {response.text}")
    print()
    
except requests.exceptions.RequestException as e:
    print(f"Error: {e}")
