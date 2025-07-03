#!/usr/bin/env python3

import requests
import json

# Configuration
BASE_URL = "https://bondy-backend-python-mi3a.onrender.com"
# BASE_URL = "http://localhost:8083"  # Uncomment for local testing

def test_basic_endpoints():
    """Test basic server endpoints"""
    print("=" * 50)
    print("TESTING BASIC ENDPOINTS")
    print("=" * 50)
    
    endpoints = [
        ("GET", "/", "Root endpoint"),
        ("GET", "/health", "Health check"),
        ("GET", "/groups", "List active groups"),
        ("GET", "/users", "List all users"),
    ]
    
    for method, path, description in endpoints:
        try:
            print(f"\n{description}: {method} {path}") 
            response = requests.get(f"{BASE_URL}{path}", timeout=10)
            print(f"Status: {response.status_code}")
            print(f"Content: {response.text}")
            
            if response.headers.get('content-type') == 'application/json':
                try:
                    json_data = response.json()
                    print(f"JSON: {json.dumps(json_data, indent=2)}")
                except:
                    pass
                    
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
        
        print("-" * 40)

def test_system_control():
    """Test system control endpoints"""
    print("\n" + "=" * 50)
    print("TESTING SYSTEM CONTROL")
    print("=" * 50)
    
    # Test health before changes
    print("\n1. Initial health check:")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Content: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test fall (system down)
    print("\n2. Setting system down:")
    try:
        response = requests.post(f"{BASE_URL}/fall", timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Content: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test health after fall
    print("\n3. Health check after fall:")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Content: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test revive (system up)
    print("\n4. Reviving system:")
    try:
        response = requests.post(f"{BASE_URL}/revive", timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Content: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test health after revive
    print("\n5. Health check after revive:")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Content: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_basic_endpoints()
    test_system_control()
