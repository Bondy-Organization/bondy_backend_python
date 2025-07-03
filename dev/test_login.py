#!/usr/bin/env python3

import requests
import json
import time

# Test login endpoint
print("Testing /login endpoint...")

# Test data
test_users = [
    {"username": "alice"},
    {"username": "bob"},
    {"username": "charlie"},
    {"username": "alice"}  # Test existing user
]

def test_login(base_url, username):
    """Test login with a specific username"""
    print(f"\nTesting login with username: '{username}'")
    
    try:
        # Prepare the request
        url = f"{base_url}/login"
        headers = {'Content-Type': 'application/json'}
        data = {"username": username}
        
        print(f"POST {url}")
        print(f"Request body: {json.dumps(data)}")
        
        # Send the request
        response = requests.post(url, json=data, headers=headers, timeout=10)
        
        print(f"Status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        try:
            response_json = response.json()
            print(f"Response body: {json.dumps(response_json, indent=2)}")
            
            # Check if user was created or already existed
            if 'created' in response_json and response_json['created']:
                print(f"✅ New user created with ID: {response_json['user_id']}")
            elif 'user_id' in response_json:
                print(f"✅ Existing user found with ID: {response_json['user_id']}")
            else:
                print("❌ Unexpected response format")
                
        except json.JSONDecodeError:
            print(f"Response text: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
    
    print("-" * 50)

def test_login_error_cases(base_url):
    """Test error cases for login"""
    print("\nTesting error cases...")
    
    # Test missing username
    print("\nTest 1: Missing username")
    try:
        url = f"{base_url}/login"
        headers = {'Content-Type': 'application/json'}
        data = {}  # No username
        
        response = requests.post(url, json=data, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 400:
            print("✅ Correctly returned 400 for missing username")
        else:
            print("❌ Expected 400 status code")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test empty username
    print("\nTest 2: Empty username")
    try:
        url = f"{base_url}/login"
        headers = {'Content-Type': 'application/json'}
        data = {"username": ""}  # Empty username
        
        response = requests.post(url, json=data, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test invalid JSON
    print("\nTest 3: Invalid JSON")
    try:
        url = f"{base_url}/login"
        headers = {'Content-Type': 'application/json'}
        
        response = requests.post(url, data="invalid json", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

# Test local server
print("=" * 60)
print("TESTING LOCAL SERVER")
print("=" * 60)

local_base_url = "http://localhost:8083"

# Test normal login cases
for user_data in test_users:
    test_login(local_base_url, user_data["username"])

# Test error cases
test_login_error_cases(local_base_url)

# Test remote server
print("\n" + "=" * 60)
print("TESTING REMOTE SERVER")
print("=" * 60)

remote_base_url = "https://bondy-backend-python-mi3a.onrender.com"

# Test normal login cases
for user_data in test_users:
    test_login(remote_base_url, user_data["username"])

# Test error cases
test_login_error_cases(remote_base_url)

print("\n" + "=" * 60)
print("TESTING COMPLETED")
print("=" * 60)
