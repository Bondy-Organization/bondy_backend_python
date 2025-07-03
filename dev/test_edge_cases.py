#!/usr/bin/env python3

import requests
import time
import json

# Configuration
BASE_URL = "https://bondy-backend-python-mi3a.onrender.com"
# BASE_URL = "http://localhost:8083"  # Uncomment for local testing

def test_error_conditions():
    """Test various error conditions and edge cases"""
    print("=" * 50)
    print("TESTING ERROR CONDITIONS & EDGE CASES")
    print("=" * 50)
    
    # 1. Test invalid endpoints
    print("\n1. Testing invalid endpoints:")
    invalid_endpoints = [
        "/invalid",
        "/user",
        "/user/",
        "/user/alice",
        "/user/alice/invalid",
        "/notify",
        "/notify/",
        "/subscribe",
        "/subscribe/invalid",
    ]
    
    for endpoint in invalid_endpoints:
        try:
            print(f"Testing {endpoint}:")
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
            print(f"  Status: {response.status_code}")
            print(f"  Content: {response.text}")
        except Exception as e:
            print(f"  Error: {e}")
    
    # 2. Test invalid HTTP methods
    print("\n2. Testing invalid HTTP methods:")
    invalid_methods = [
        ("PUT", "/health"),
        ("PATCH", "/health"),
        ("DELETE", "/health"),
        ("POST", "/health"),
        ("PUT", "/groups"),
        ("DELETE", "/groups"),
    ]
    
    for method, endpoint in invalid_methods:
        try:
            print(f"Testing {method} {endpoint}:")
            response = requests.request(method, f"{BASE_URL}{endpoint}", timeout=10)
            print(f"  Status: {response.status_code}")
            print(f"  Content: {response.text}")
        except Exception as e:
            print(f"  Error: {e}")
    
    # 3. Test invalid JSON payloads
    print("\n3. Testing invalid JSON payloads:")
    
    # Invalid JSON for user groups
    print("Testing invalid JSON for user groups:")
    invalid_payloads = [
        {},  # Missing groups
        {"groups": "not_an_array"},  # Groups not an array
        {"invalid": ["group1"]},  # Wrong key
        {"groups": []},  # Empty groups (should work but remove user)
    ]
    
    for payload in invalid_payloads:
        try:
            print(f"Testing payload: {payload}")
            response = requests.post(
                f"{BASE_URL}/user/testuser/groups",
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            print(f"  Status: {response.status_code}")
            print(f"  Content: {response.text}")
        except Exception as e:
            print(f"  Error: {e}")
    
    # 4. Test missing query parameters
    print("\n4. Testing missing query parameters:")
    
    # Subscribe user without user_id
    try:
        print("Testing /subscribe/user without user_id:")
        response = requests.get(f"{BASE_URL}/subscribe/user", timeout=10)
        print(f"  Status: {response.status_code}")
        print(f"  Content: {response.text}")
    except Exception as e:
        print(f"  Error: {e}")
    
    # 5. Test very long group/user names
    print("\n5. Testing very long names:")
    long_name = "a" * 1000  # Very long name
    
    try:
        print("Testing very long user name:")
        response = requests.get(f"{BASE_URL}/user/{long_name}/groups", timeout=10)
        print(f"  Status: {response.status_code}")
        print(f"  Content: {response.text}")
    except Exception as e:
        print(f"  Error: {e}")
    
    # 6. Test special characters in names
    print("\n6. Testing special characters:")
    special_names = [
        "user@domain.com",
        "user with spaces",
        "user/with/slashes",
        "user?with=query",
        "user#with%encoding",
    ]
    
    for name in special_names:
        try:
            print(f"Testing user name: '{name}'")
            response = requests.get(f"{BASE_URL}/user/{name}/groups", timeout=10)
            print(f"  Status: {response.status_code}")
            print(f"  Content: {response.text}")
        except Exception as e:
            print(f"  Error: {e}")

def test_system_down_behavior():
    """Test behavior when system is down"""
    print("\n" + "=" * 50)
    print("TESTING SYSTEM DOWN BEHAVIOR")
    print("=" * 50)
    
    # 1. Set system down
    print("\n1. Setting system down:")
    try:
        response = requests.post(f"{BASE_URL}/fall", timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Content: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # 2. Test various endpoints when system is down
    print("\n2. Testing endpoints when system is down:")
    endpoints_when_down = [
        "/groups",
        "/users", 
        "/user/alice/groups",
        "/subscribe/status?group=test",
        "/subscribe/user?user_id=alice",
    ]
    
    for endpoint in endpoints_when_down:
        try:
            print(f"Testing {endpoint}:")
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
            print(f"  Status: {response.status_code}")
            print(f"  Content: {response.text}")
        except Exception as e:
            print(f"  Error: {e}")
    
    # 3. Test that health and control endpoints still work
    print("\n3. Testing that control endpoints still work when down:")
    control_endpoints = [
        ("GET", "/health"),
        ("POST", "/revive"),
    ]
    
    for method, endpoint in control_endpoints:
        try:
            print(f"Testing {method} {endpoint}:")
            response = requests.request(method, f"{BASE_URL}{endpoint}", timeout=10)
            print(f"  Status: {response.status_code}")
            print(f"  Content: {response.text}")
        except Exception as e:
            print(f"  Error: {e}")
    
    # 4. Revive system
    print("\n4. Reviving system:")
    try:
        response = requests.post(f"{BASE_URL}/revive", timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Content: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_error_conditions()
    test_system_down_behavior()
