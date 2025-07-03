#!/usr/bin/env python3

import requests
import threading
import time
import json

# Configuration
BASE_URL = "https://bondy-backend-python-mi3a.onrender.com"
# BASE_URL = "http://localhost:8083"  # Uncomment for local testing

def test_long_polling():
    """Test long-polling endpoints"""
    print("=" * 50)
    print("TESTING LONG-POLLING (NOTIFICATIONS)")
    print("=" * 50)
    
    # Set up some users and groups first
    print("\n1. Setting up users and groups for testing:")
    setup_data = [
        ("alice", ["frontend", "admin"]),
        ("bob", ["backend", "admin"]),
        ("charlie", ["frontend", "notifications"])
    ]
    
    for user, groups in setup_data:
        try:
            payload = {"groups": groups}
            response = requests.post(
                f"{BASE_URL}/user/{user}/groups", 
                json=payload, 
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            print(f"Setup {user} with groups {groups}: {response.status_code}")
        except Exception as e:
            print(f"Error setting up {user}: {e}")
    
    print("\n2. Testing group-specific long-polling:")
    
    def long_poll_group(group_name, duration=10):
        """Long poll for a specific group"""
        print(f"[Thread] Starting long-poll for group '{group_name}'")
        try:
            response = requests.get(
                f"{BASE_URL}/subscribe/status?group={group_name}", 
                timeout=duration + 5
            )
            print(f"[Thread] Long-poll for '{group_name}' completed:")
            print(f"[Thread] Status: {response.status_code}")
            print(f"[Thread] Content: {response.text}")
        except requests.exceptions.Timeout:
            print(f"[Thread] Long-poll for '{group_name}' timed out (expected)")
        except Exception as e:
            print(f"[Thread] Error in long-poll for '{group_name}': {e}")
    
    def long_poll_user(user_id, duration=10):
        """Long poll for a specific user"""
        print(f"[Thread] Starting long-poll for user '{user_id}'")
        try:
            response = requests.get(
                f"{BASE_URL}/subscribe/user?user_id={user_id}", 
                timeout=duration + 5
            )
            print(f"[Thread] Long-poll for user '{user_id}' completed:")
            print(f"[Thread] Status: {response.status_code}")
            print(f"[Thread] Content: {response.text}")
        except requests.exceptions.Timeout:
            print(f"[Thread] Long-poll for user '{user_id}' timed out (expected)")
        except Exception as e:
            print(f"[Thread] Error in long-poll for user '{user_id}': {e}")
    
    # Start background long-polling threads
    print("\nStarting background long-polling threads...")
    threads = []
    
    # Group-based long polling
    group_thread = threading.Thread(target=long_poll_group, args=("frontend", 15))
    group_thread.start()
    threads.append(group_thread)
    
    # User-based long polling
    user_thread = threading.Thread(target=long_poll_user, args=("alice", 15))
    user_thread.start()
    threads.append(user_thread)
    
    # Wait a bit for threads to start
    time.sleep(2)
    
    # Test notifications
    print("\n3. Testing notifications:")
    
    # Notify specific group
    print("\nNotifying 'frontend' group:")
    try:
        response = requests.post(f"{BASE_URL}/notify/frontend", timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Content: {response.text}")
    except Exception as e:
        print(f"Error notifying frontend: {e}")
    
    # Wait a bit
    time.sleep(3)
    
    # Notify all groups
    print("\nNotifying all groups:")
    try:
        response = requests.post(f"{BASE_URL}/notify/all", timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Content: {response.text}")
    except Exception as e:
        print(f"Error notifying all: {e}")
    
    # Wait for threads to complete
    print("\nWaiting for long-polling threads to complete...")
    for thread in threads:
        thread.join(timeout=20)
    
    print("\nLong-polling test completed!")

def test_short_timeout_polling():
    """Test long-polling with short timeout to verify timeout behavior"""
    print("\n" + "=" * 50)
    print("TESTING SHORT TIMEOUT POLLING")
    print("=" * 50)
    
    print("\nTesting group polling with 3-second timeout (should timeout):")
    try:
        start_time = time.time()
        response = requests.get(f"{BASE_URL}/subscribe/status?group=test", timeout=5)
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"Status: {response.status_code}")
        print(f"Content: {response.text}")
        print(f"Duration: {duration:.2f} seconds")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\nTesting user polling with 3-second timeout (should timeout):")
    try:
        start_time = time.time()
        response = requests.get(f"{BASE_URL}/subscribe/user?user_id=testuser", timeout=5)
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"Status: {response.status_code}")
        print(f"Content: {response.text}")
        print(f"Duration: {duration:.2f} seconds")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_long_polling()
    test_short_timeout_polling()
