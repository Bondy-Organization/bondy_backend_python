#!/usr/bin/env python3

import requests
import json

# Configuration
BASE_URL = "https://bondy-backend-python-mi3a.onrender.com"
# BASE_URL = "http://localhost:8083"  # Uncomment for local testing

def test_user_group_management():
    """Test user-group management endpoints"""
    print("=" * 50)
    print("TESTING USER-GROUP MANAGEMENT")
    print("=" * 50)
    
    # Test users and groups
    users = ["alice", "bob", "charlie"]
    groups = ["frontend", "backend", "admin", "notifications"]
    
    # 1. Initial state
    print("\n1. Initial users and groups:")
    try:
        response = requests.get(f"{BASE_URL}/users", timeout=10)
        print(f"Users - Status: {response.status_code}")
        print(f"Users - Content: {response.text}")
        
        response = requests.get(f"{BASE_URL}/groups", timeout=10)
        print(f"Groups - Status: {response.status_code}")
        print(f"Groups - Content: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # 2. Add users to groups individually
    print("\n2. Adding users to groups individually:")
    user_group_assignments = [
        ("alice", "frontend"),
        ("alice", "admin"),
        ("bob", "backend"),
        ("bob", "admin"),
        ("charlie", "frontend"),
        ("charlie", "notifications"),
    ]
    
    for user, group in user_group_assignments:
        try:
            print(f"Adding {user} to {group}...")
            response = requests.post(f"{BASE_URL}/user/{user}/groups/{group}", timeout=10)
            print(f"Status: {response.status_code}")
            print(f"Content: {response.text}")
        except Exception as e:
            print(f"Error adding {user} to {group}: {e}")
    
    # 3. Check user groups
    print("\n3. Checking individual user groups:")
    for user in users:
        try:
            print(f"Groups for {user}:")
            response = requests.get(f"{BASE_URL}/user/{user}/groups", timeout=10)
            print(f"Status: {response.status_code}")
            print(f"Content: {response.text}")
        except Exception as e:
            print(f"Error getting groups for {user}: {e}")
    
    # 4. Set all groups for a user at once
    print("\n4. Setting all groups for alice at once:")
    try:
        new_groups = ["frontend", "backend", "admin", "notifications"]
        payload = {"groups": new_groups}
        response = requests.post(
            f"{BASE_URL}/user/alice/groups", 
            json=payload, 
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        print(f"Status: {response.status_code}")
        print(f"Content: {response.text}")
    except Exception as e:
        print(f"Error setting groups for alice: {e}")
    
    # 5. Check all users after changes
    print("\n5. Final state - all users:")
    try:
        response = requests.get(f"{BASE_URL}/users", timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Content: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    
    # 6. Remove user from group
    print("\n6. Removing charlie from notifications:")
    try:
        response = requests.delete(f"{BASE_URL}/user/charlie/groups/notifications", timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Content: {response.text}")
    except Exception as e:
        print(f"Error removing charlie from notifications: {e}")
    
    # 7. Final check
    print("\n7. Final check - charlie's groups:")
    try:
        response = requests.get(f"{BASE_URL}/user/charlie/groups", timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Content: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_user_group_management()
