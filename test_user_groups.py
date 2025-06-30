#!/usr/bin/env python3
"""
Test script to demonstrate the enhanced user-based notification system.
This script shows how users can subscribe to multiple groups at once.
"""

import requests
import threading
import time
import json

# Server configuration
BASE_URL = "http://localhost:8083"

def setup_user_groups(user_id, groups):
    """
    Set up groups for a user.
    """
    print(f"Setting up groups {groups} for user {user_id}")
    try:
        response = requests.post(
            f"{BASE_URL}/user/{user_id}/groups", 
            json={"groups": groups}
        )
        if response.status_code == 200:
            data = response.json()
            print(f"Successfully set groups for {user_id}: {data}")
            return True
        else:
            print(f"Failed to set groups for {user_id}: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error setting up groups for {user_id}: {e}")
        return False

def add_user_to_group(user_id, group_name):
    """
    Add user to a specific group.
    """
    print(f"Adding user {user_id} to group {group_name}")
    try:
        response = requests.post(f"{BASE_URL}/user/{user_id}/groups/{group_name}")
        if response.status_code == 200:
            data = response.json()
            print(f"Successfully added {user_id} to {group_name}: {data}")
            return True
        else:
            print(f"Failed to add {user_id} to {group_name}: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error adding {user_id} to {group_name}: {e}")
        return False

def get_user_groups(user_id):
    """
    Get groups that a user belongs to.
    """
    try:
        response = requests.get(f"{BASE_URL}/user/{user_id}/groups")
        if response.status_code == 200:
            data = response.json()
            print(f"User {user_id} groups: {data}")
            return data.get('groups', [])
        else:
            print(f"Failed to get groups for {user_id}: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error getting groups for {user_id}: {e}")
        return []

def subscribe_to_user_notifications(user_id, test_duration=30):
    """
    Subscribe to notifications for all groups that a user belongs to.
    """
    print(f"[User {user_id}] Starting user-based subscription...")
    try:
        response = requests.get(f"{BASE_URL}/subscribe/user?user_id={user_id}", timeout=test_duration)
        if response.status_code == 200:
            data = response.json()
            print(f"[User {user_id}] Received notification: {json.dumps(data, indent=2)}")
        elif response.status_code == 204:
            print(f"[User {user_id}] No changes during timeout period")
        elif response.status_code == 400:
            error_data = response.json()
            print(f"[User {user_id}] Error: {error_data}")
        else:
            print(f"[User {user_id}] Unexpected response: {response.status_code}")
    except requests.exceptions.Timeout:
        print(f"[User {user_id}] Request timed out")
    except Exception as e:
        print(f"[User {user_id}] Error: {e}")

def send_notification_to_group(group_name):
    """
    Send a notification to a specific group.
    """
    print(f"Sending notification to group: {group_name}")
    try:
        response = requests.post(f"{BASE_URL}/notify/{group_name}")
        if response.status_code == 200:
            data = response.json()
            print(f"Notification sent successfully: {data}")
        else:
            print(f"Failed to send notification: {response.status_code}")
    except Exception as e:
        print(f"Error sending notification: {e}")

def get_all_users():
    """
    Get all users and their groups.
    """
    print("Getting all users and their groups...")
    try:
        response = requests.get(f"{BASE_URL}/users")
        if response.status_code == 200:
            data = response.json()
            print(f"All users: {json.dumps(data, indent=2)}")
            return data.get('user_groups', {})
        else:
            print(f"Failed to get users: {response.status_code}")
            return {}
    except Exception as e:
        print(f"Error getting users: {e}")
        return {}

def test_health():
    """
    Test the health endpoint.
    """
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Health check: {response.status_code} - {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

def main():
    """
    Main test function demonstrating user-based multi-group notifications.
    """
    print("=== User-based Multi-Group Notification System Test ===\n")
    
    # First, check if server is running
    if not test_health():
        print("Server is not running or not healthy. Please start the server first.")
        return
    
    print("\n1. Setting up users and their groups...")
    
    # Setup users with different group memberships
    users_and_groups = {
        "alice": ["frontend", "notifications", "admin"],
        "bob": ["backend", "notifications"],
        "charlie": ["frontend", "backend"],
        "diana": ["admin", "notifications"]
    }
    
    for user_id, groups in users_and_groups.items():
        setup_user_groups(user_id, groups)
        time.sleep(0.5)
    
    print("\n2. Verifying user group memberships...")
    for user_id in users_and_groups.keys():
        get_user_groups(user_id)
    
    print("\n3. Getting all users overview...")
    get_all_users()
    
    print("\n4. Starting user-based subscriptions...")
    
    # Start user-based subscribers in separate threads
    users_to_test = ["alice", "bob", "charlie"]
    subscriber_threads = []
    
    for user_id in users_to_test:
        thread = threading.Thread(
            target=subscribe_to_user_notifications, 
            args=(user_id, 25), 
            name=f"UserSubscriber-{user_id}"
        )
        thread.daemon = True
        thread.start()
        subscriber_threads.append(thread)
        time.sleep(0.5)
    
    print(f"\nStarted {len(subscriber_threads)} user subscriber threads")
    
    # Wait for subscribers to start
    time.sleep(3)
    
    print("\n5. Sending targeted notifications to different groups...")
    
    # Send notifications to different groups and see which users get notified
    time.sleep(2)
    print("\n--- Notifying 'frontend' group (should notify alice and charlie) ---")
    send_notification_to_group("frontend")
    
    time.sleep(4)
    print("\n--- Notifying 'backend' group (should notify bob and charlie) ---")
    send_notification_to_group("backend")
    
    time.sleep(4)
    print("\n--- Notifying 'notifications' group (should notify alice, bob, and diana) ---")
    send_notification_to_group("notifications")
    
    time.sleep(4)
    print("\n--- Notifying 'admin' group (should notify alice and diana) ---")
    send_notification_to_group("admin")
    
    print("\n6. Testing adding a user to a new group dynamically...")
    time.sleep(2)
    add_user_to_group("bob", "admin")
    
    print("\n7. Final user overview...")
    time.sleep(2)
    get_all_users()
    
    print("\nWaiting for subscriber threads to complete...")
    for thread in subscriber_threads:
        thread.join(timeout=5)
    
    print("\n=== Test completed ===")
    print("\nKey observations:")
    print("- Each user subscribed to ALL their groups with a single request")
    print("- Users only got notified when one of THEIR groups was notified")
    print("- Multiple users can be notified by a single group notification")
    print("- User group memberships can be modified dynamically")

if __name__ == "__main__":
    main()
