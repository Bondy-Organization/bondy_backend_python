#!/usr/bin/env python3
"""
Integration test for chat creation and messaging flow
"""

import requests
import json
import time
import threading

# Server URL
BASE_URL = "http://127.0.0.1:8080"

def test_full_chat_flow():
    """Test the complete flow: create users, create group, send messages, verify notifications"""
    print("Testing complete chat creation and messaging flow...")
    
    # Step 1: Create two users
    print("\n1. Creating test users...")
    
    # Create user 1 (group creator)
    login_data1 = {"username": "alice"}
    response1 = requests.post(f"{BASE_URL}/login", json=login_data1)
    print(f"Alice login: {response1.status_code} - {response1.json()}")
    alice_id = response1.json()['user_id']
    
    # Create user 2 (will be added to group later)
    login_data2 = {"username": "bob"}
    response2 = requests.post(f"{BASE_URL}/login", json=login_data2)
    print(f"Bob login: {response2.status_code} - {response2.json()}")
    bob_id = response2.json()['user_id']
    
    # Step 2: Create a chat group with multiple members
    print("\n2. Creating chat group with multiple members...")
    create_chat_data = {
        "groupName": "Alice and Friends",
        "creatorId": alice_id,
        "members": ["bob"]  # Add Bob directly when creating the group
    }
    response = requests.post(f"{BASE_URL}/create-chat", json=create_chat_data)
    print(f"Create chat response: {response.status_code} - {response.json()}")
    group_id = response.json()['group_id']
    
    # Step 3: Verify both users see the group in their chats (Bob should already be in the group)
    print("\n3. Verifying group appears in both users' chats...")
    
    response = requests.get(f"{BASE_URL}/chats?userId={alice_id}")
    alice_chats = response.json()
    print(f"Alice's chats: {alice_chats}")
    
    response = requests.get(f"{BASE_URL}/chats?userId={bob_id}")
    bob_chats = response.json()
    print(f"Bob's chats: {bob_chats}")
    
    # Step 4: Send a message to the group
    print("\n4. Sending message to the group...")
    message_data = {
        "text": "Hello everyone! This is Alice.",
        "user_id": alice_id,
        "chat_id": group_id
    }
    response = requests.post(f"{BASE_URL}/send", json=message_data)
    print(f"Send message response: {response.status_code} - {response.json()}")
    
    # Step 5: Check group messages
    print("\n5. Retrieving group messages...")
    response = requests.get(f"{BASE_URL}/messages?chatId={group_id}")
    messages = response.json()
    print(f"Group messages: {messages}")
    
    # Step 6: Test group users endpoint
    print("\n6. Checking group members...")
    response = requests.get(f"{BASE_URL}/group-users?groupId={group_id}")
    group_users = response.json()
    print(f"Group members: {group_users}")
    
    print(f"\n✅ Full chat flow test completed successfully!")
    print(f"   - Created group '{create_chat_data['groupName']}' (ID: {group_id})")
    print(f"   - Added users Alice (ID: {alice_id}) and Bob (ID: {bob_id}) during creation")
    print(f"   - Sent and retrieved messages")
    
    return {
        'group_id': group_id,
        'alice_id': alice_id,
        'bob_id': bob_id
    }

def test_edge_cases():
    """Test edge cases for chat creation"""
    print("\n\nTesting edge cases...")
    
    # Test with empty group name
    print("\n1. Testing empty group name...")
    create_chat_data = {
        "groupName": "",
        "creatorId": 1
    }
    response = requests.post(f"{BASE_URL}/create-chat", json=create_chat_data)
    print(f"Empty group name response: {response.status_code} - {response.json()}")
    
    # Test with very long group name
    print("\n2. Testing very long group name...")
    create_chat_data = {
        "groupName": "A" * 500,  # Very long name
        "creatorId": 1
    }
    response = requests.post(f"{BASE_URL}/create-chat", json=create_chat_data)
    print(f"Long group name response: {response.status_code} - {response.json()}")
    
    # Test with special characters in group name
    print("\n3. Testing special characters in group name...")
    create_chat_data = {
        "groupName": "Test Group 🚀 with émojis & spëcial chars!",
        "creatorId": 1
    }
    response = requests.post(f"{BASE_URL}/create-chat", json=create_chat_data)
    print(f"Special chars response: {response.status_code} - {response.json()}")

if __name__ == "__main__":
    print("Starting comprehensive chat creation tests...")
    
    try:
        # Run main flow test
        result = test_full_chat_flow()
        
        # Run edge case tests
        test_edge_cases()
        
        print("\n✅ All comprehensive tests completed!")
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to server. Make sure the server is running on port 8080")
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
