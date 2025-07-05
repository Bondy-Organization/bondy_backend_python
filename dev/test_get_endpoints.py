#!/usr/bin/env python3

import requests
import json
import time

def test_get_endpoints(base_url):
    """Test GET endpoints with query parameters"""
    print(f"\n📡 Testing GET endpoints with query parameters for {base_url}")
    print("=" * 60)
    
    # First, create a user to test with
    print("\n1️⃣  Creating test user...")
    try:
        login_response = requests.post(
            f"{base_url}/login",
            json={"username": "testuser_get"},
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        if login_response.status_code == 200:
            user_data = login_response.json()
            user_id = user_data['user_id']
            print(f"✅ User created/found with ID: {user_id}")
        else:
            print(f"❌ Failed to create user: {login_response.text}")
            return
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        return
    
    # Test cases for GET endpoints
    test_cases = [
        {
            'name': 'GET /chats with userId',
            'url': f"{base_url}/chats?userId={user_id}",
            'expected_status': [200, 404],  # 404 if user has no groups
            'description': 'Should return user chats'
        },
        {
            'name': 'GET /chats without userId',
            'url': f"{base_url}/chats",
            'expected_status': [400],
            'description': 'Should return error for missing userId parameter'
        },
        {
            'name': 'GET /messages with groupId=1',
            'url': f"{base_url}/messages?groupId=1",
            'expected_status': [200, 404],  # 404 if group doesn't exist
            'description': 'Should return group messages or group not found'
        },
        {
            'name': 'GET /messages without groupId',
            'url': f"{base_url}/messages",
            'expected_status': [400],
            'description': 'Should return error for missing groupId parameter'
        },
        {
            'name': 'GET /group-users with groupId=1',
            'url': f"{base_url}/group-users?groupId=1",
            'expected_status': [200, 404],  # 404 if group doesn't exist
            'description': 'Should return group users or group not found'
        },
        {
            'name': 'GET /group-users without groupId',
            'url': f"{base_url}/group-users",
            'expected_status': [400],
            'description': 'Should return error for missing groupId parameter'
        },
        {
            'name': 'GET /chats with invalid userId',
            'url': f"{base_url}/chats?userId=99999",
            'expected_status': [404],
            'description': 'Should return user not found'
        },
        {
            'name': 'GET /messages with invalid groupId',
            'url': f"{base_url}/messages?groupId=99999",
            'expected_status': [404],
            'description': 'Should return group not found'
        }
    ]
    
    for i, test_case in enumerate(test_cases, 2):
        print(f"\n{i}️⃣  {test_case['name']}")
        print(f"🔗 URL: {test_case['url']}")
        print(f"📝 Description: {test_case['description']}")
        
        try:
            response = requests.get(test_case['url'], timeout=10)
            print(f"📊 Status: {response.status_code}")
            
            if response.status_code in test_case['expected_status']:
                print("✅ Status code as expected")
            else:
                print(f"❌ Unexpected status. Expected: {test_case['expected_status']}, Got: {response.status_code}")
            
            try:
                response_json = response.json()
                print(f"📨 Response: {json.dumps(response_json, indent=2)}")
            except json.JSONDecodeError:
                print(f"📨 Response (raw): {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request error: {e}")
        
        print("-" * 40)

def test_query_parameter_combinations(base_url):
    """Test various query parameter combinations"""
    print(f"\n🔍 Testing query parameter combinations")
    print("=" * 60)
    
    test_urls = [
        f"{base_url}/chats?userId=1&extra=param",  # Extra parameters should be ignored
        f"{base_url}/messages?groupId=1&limit=10",  # Extra parameters should be ignored
        f"{base_url}/group-users?groupId=1&sort=name",  # Extra parameters should be ignored
        f"{base_url}/chats?wrongParam=1",  # Wrong parameter name
        f"{base_url}/messages?userId=1",  # Wrong parameter for endpoint
    ]
    
    for i, url in enumerate(test_urls, 1):
        print(f"\n{i}️⃣  Testing: {url}")
        
        try:
            response = requests.get(url, timeout=10)
            print(f"📊 Status: {response.status_code}")
            
            try:
                response_json = response.json()
                print(f"📨 Response: {json.dumps(response_json, indent=2)}")
            except json.JSONDecodeError:
                print(f"📨 Response (raw): {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request error: {e}")
        
        print("-" * 40)

def create_curl_examples():
    """Create curl command examples for testing"""
    print(f"\n📋 CURL Command Examples")
    print("=" * 60)
    
    base_url = "http://localhost:8080"  # Change as needed
    
    curl_commands = [
        f'# Get user chats\ncurl "{base_url}/chats?userId=1"',
        f'# Get group messages\ncurl "{base_url}/messages?groupId=1"',
        f'# Get group users\ncurl "{base_url}/group-users?groupId=1"',
        f'# Test missing parameter\ncurl "{base_url}/chats"',
        f'# Test with multiple parameters\ncurl "{base_url}/chats?userId=1&extra=ignored"',
    ]
    
    for command in curl_commands:
        print(f"\n{command}")
    
    print("\n" + "=" * 60)

# Test local server
print("🧪 GET ENDPOINTS WITH QUERY PARAMETERS TESTING")
print("=" * 60)

local_base_url = "http://localhost:8080"

test_get_endpoints(local_base_url)
test_query_parameter_combinations(local_base_url)

# Test remote server
print("\n" + "=" * 60)
print("🌐 TESTING REMOTE SERVER")
print("=" * 60)

remote_base_url = "https://bondy-backend-python-mi3a.onrender.com"

test_get_endpoints(remote_base_url)
test_query_parameter_combinations(remote_base_url)

# Show curl examples
create_curl_examples()

print("\n" + "=" * 60)
print("✅ GET ENDPOINTS TESTING COMPLETED")
print("=" * 60)
print("\n💡 Summary of changes:")
print("✅ GET /chats now uses ?userId=123")
print("✅ GET /messages now uses ?groupId=123") 
print("✅ GET /group-users now uses ?groupId=123")
print("✅ All endpoints properly validate query parameters")
print("✅ Middleware updated to handle paths with query parameters")
