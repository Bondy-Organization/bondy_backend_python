#!/usr/bin/env python3
"""
Test script for the /create-chat endpoint
"""

import requests
import json

# Server URL
BASE_URL = "http://127.0.0.1:8080"

def test_create_chat():
    """Test creating a new chat group"""
    print("Testing /create-chat endpoint...")
    
    # First, create a user to be the group creator
    print("\n1. Creating a test user first...")
    login_data = {"username": "testcreator"}
    response = requests.post(f"{BASE_URL}/login", json=login_data)
    print(f"Login response: {response.status_code} - {response.json()}")
    
    if response.status_code == 200:
        creator_id = response.json()['user_id']
        print(f"Creator user ID: {creator_id}")
        
        # Test creating a new chat group
        print("\n2. Creating a new chat group...")
        create_chat_data = {
            "groupName": "Test Group",
            "creatorId": creator_id
        }
        response = requests.post(f"{BASE_URL}/create-chat", json=create_chat_data)
        print(f"Create chat response: {response.status_code} - {response.json()}")
        
        if response.status_code == 200:
            group_data = response.json()
            group_id = group_data['group_id']
            print(f"Successfully created group: {group_data}")
            
            # Test creating a group with duplicate name
            print("\n3. Testing duplicate group name...")
            response = requests.post(f"{BASE_URL}/create-chat", json=create_chat_data)
            print(f"Duplicate name response: {response.status_code} - {response.json()}")
            
            # Test creating a group with non-existent creator
            print("\n4. Testing non-existent creator...")
            invalid_data = {
                "groupName": "Another Test Group",
                "creatorId": 99999
            }
            response = requests.post(f"{BASE_URL}/create-chat", json=invalid_data)
            print(f"Invalid creator response: {response.status_code} - {response.json()}")
            
            # Test missing required fields
            print("\n5. Testing missing required fields...")
            incomplete_data = {"groupName": "Incomplete Group"}
            response = requests.post(f"{BASE_URL}/create-chat", json=incomplete_data)
            print(f"Missing field response: {response.status_code} - {response.json()}")
            
            # Test empty request body
            print("\n6. Testing empty request body...")
            response = requests.post(f"{BASE_URL}/create-chat", json={})
            print(f"Empty body response: {response.status_code} - {response.json()}")
            
            # Verify the group appears in user's chats
            print("\n7. Verifying group appears in user's chats...")
            response = requests.get(f"{BASE_URL}/chats?userId={creator_id}")
            print(f"User chats response: {response.status_code} - {response.json()}")
            
            return group_id
    else:
        print("Failed to create test user")
        return None

def test_cors_for_create_chat():
    """Test CORS preflight for /create-chat endpoint"""
    print("\n\nTesting CORS preflight for /create-chat...")
    
    # Test OPTIONS request
    response = requests.options(f"{BASE_URL}/create-chat")
    print(f"OPTIONS response: {response.status_code}")
    print(f"CORS headers: {dict(response.headers)}")

if __name__ == "__main__":
    print("Starting /create-chat endpoint tests...")
    
    try:
        group_id = test_create_chat()
        test_cors_for_create_chat()
        
        if group_id:
            print(f"\n✅ All tests completed. Created group ID: {group_id}")
        else:
            print("\n❌ Some tests failed")
            
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to server. Make sure the server is running on port 8080")
    except Exception as e:
        print(f"❌ Error during testing: {e}")
