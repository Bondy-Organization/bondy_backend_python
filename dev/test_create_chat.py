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
    
    # First, create test users
    print("\n1. Creating test users first...")
    login_data1 = {"username": "testcreator"}
    response1 = requests.post(f"{BASE_URL}/login", json=login_data1)
    print(f"Creator login response: {response1.status_code} - {response1.json()}")
    
    login_data2 = {"username": "member1"}
    response2 = requests.post(f"{BASE_URL}/login", json=login_data2)
    print(f"Member1 login response: {response2.status_code} - {response2.json()}")
    
    login_data3 = {"username": "member2"}
    response3 = requests.post(f"{BASE_URL}/login", json=login_data3)
    print(f"Member2 login response: {response3.status_code} - {response3.json()}")
    
    if response1.status_code == 200:
        creator_id = response1.json()['user_id']
        print(f"Creator user ID: {creator_id}")
        
        # Test creating a new chat group without additional members
        print("\n2. Creating a new chat group (creator only)...")
        create_chat_data = {
            "groupName": "Test Group",
            "creatorId": creator_id
        }
        response = requests.post(f"{BASE_URL}/create-chat", json=create_chat_data)
        print(f"Create chat response: {response.status_code} - {response.json()}")
        
        if response.status_code == 200:
            group_data = response.json()
            print(f"Successfully created group: {group_data}")
            
            # Test creating a group with multiple members
            print("\n3. Creating a group with multiple members...")
            create_chat_with_members = {
                "groupName": "Group With Members",
                "creatorId": creator_id,
                "members": ["member1", "member2"]
            }
            response = requests.post(f"{BASE_URL}/create-chat", json=create_chat_with_members)
            print(f"Create group with members response: {response.status_code} - {response.json()}")
            
            # Test creating a group with non-existent members
            print("\n4. Creating a group with non-existent members...")
            create_chat_invalid_members = {
                "groupName": "Group With Invalid Members",
                "creatorId": creator_id,
                "members": ["member1", "nonexistent_user", "member2"]
            }
            response = requests.post(f"{BASE_URL}/create-chat", json=create_chat_invalid_members)
            print(f"Create group with invalid members response: {response.status_code} - {response.json()}")
            
            # Test creating a group with creator in members list (should not duplicate)
            print("\n5. Creating a group with creator in members list...")
            create_chat_creator_in_members = {
                "groupName": "Group Creator Duplicate Test",
                "creatorId": creator_id,
                "members": ["testcreator", "member1"]  # Creator's username in members
            }
            response = requests.post(f"{BASE_URL}/create-chat", json=create_chat_creator_in_members)
            print(f"Create group with creator in members response: {response.status_code} - {response.json()}")
            
            # Test creating a group with duplicate group name
            print("\n6. Testing duplicate group name...")
            response = requests.post(f"{BASE_URL}/create-chat", json=create_chat_data)
            print(f"Duplicate name response: {response.status_code} - {response.json()}")
            
            # Test creating a group with non-existent creator
            print("\n7. Testing non-existent creator...")
            invalid_data = {
                "groupName": "Another Test Group",
                "creatorId": 99999
            }
            response = requests.post(f"{BASE_URL}/create-chat", json=invalid_data)
            print(f"Invalid creator response: {response.status_code} - {response.json()}")
            
            # Test missing required fields
            print("\n8. Testing missing required fields...")
            incomplete_data = {"groupName": "Incomplete Group"}
            response = requests.post(f"{BASE_URL}/create-chat", json=incomplete_data)
            print(f"Missing field response: {response.status_code} - {response.json()}")
            
            # Test empty request body
            print("\n9. Testing empty request body...")
            response = requests.post(f"{BASE_URL}/create-chat", json={})
            print(f"Empty body response: {response.status_code} - {response.json()}")
            
            # Verify the groups appear in users' chats
            print("\n10. Verifying groups appear in users' chats...")
            response = requests.get(f"{BASE_URL}/chats?userId={creator_id}")
            print(f"Creator chats response: {response.status_code} - {response.json()}")
            
            if response2.status_code == 200:
                member1_id = response2.json()['user_id']
                response = requests.get(f"{BASE_URL}/chats?userId={member1_id}")
                print(f"Member1 chats response: {response.status_code} - {response.json()}")
            
            return group_data.get('group_id')
    else:
        print("Failed to create test users")
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
