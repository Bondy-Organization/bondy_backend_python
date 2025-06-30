#!/usr/bin/env python3
"""
Test script to demonstrate the group-based notification system.
This script shows how to use the new group functionality.
"""

import requests
import threading
import time
import json

# Server configuration
BASE_URL = "http://localhost:8083"

def test_subscribe_to_group(group_name, test_duration=30):
    """
    Subscribe to notifications for a specific group.
    """
    print(f"[Group {group_name}] Starting subscription...")
    try:
        response = requests.get(f"{BASE_URL}/subscribe/status?group={group_name}", timeout=test_duration)
        if response.status_code == 200:
            data = response.json()
            print(f"[Group {group_name}] Received notification: {json.dumps(data, indent=2)}")
        elif response.status_code == 204:
            print(f"[Group {group_name}] No changes during timeout period")
        else:
            print(f"[Group {group_name}] Unexpected response: {response.status_code}")
    except requests.exceptions.Timeout:
        print(f"[Group {group_name}] Request timed out")
    except Exception as e:
        print(f"[Group {group_name}] Error: {e}")

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

def get_active_groups():
    """
    Get list of active groups.
    """
    print("Getting active groups...")
    try:
        response = requests.get(f"{BASE_URL}/groups")
        if response.status_code == 200:
            data = response.json()
            print(f"Active groups: {json.dumps(data, indent=2)}")
            return data.get('active_groups', [])
        else:
            print(f"Failed to get groups: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error getting groups: {e}")
        return []

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
    Main test function demonstrating group-based notifications.
    """
    print("=== Group-based Notification System Test ===\n")
    
    # First, check if server is running
    if not test_health():
        print("Server is not running or not healthy. Please start the server first.")
        return
    
    print("\n1. Testing group subscriptions...")
    
    # Start subscribers for different groups in separate threads
    groups_to_test = ["group1", "group2", "default"]
    subscriber_threads = []
    
    for group in groups_to_test:
        thread = threading.Thread(
            target=test_subscribe_to_group, 
            args=(group, 25), 
            name=f"Subscriber-{group}"
        )
        thread.daemon = True
        thread.start()
        subscriber_threads.append(thread)
        time.sleep(0.5)  # Small delay between starting subscribers
    
    print(f"\nStarted {len(subscriber_threads)} subscriber threads")
    
    # Wait a bit for subscribers to start
    time.sleep(3)
    
    print("\n2. Checking active groups...")
    get_active_groups()
    
    print("\n3. Sending targeted notifications...")
    
    # Send notifications to specific groups
    time.sleep(2)
    send_notification_to_group("group1")
    
    time.sleep(3)
    send_notification_to_group("group2")
    
    time.sleep(3)
    send_notification_to_group("default")
    
    time.sleep(3)
    print("\n4. Sending notification to all groups...")
    send_notification_to_group("all")
    
    print("\n5. Checking active groups again...")
    time.sleep(2)
    get_active_groups()
    
    print("\nWaiting for subscriber threads to complete...")
    for thread in subscriber_threads:
        thread.join(timeout=5)
    
    print("\n=== Test completed ===")

if __name__ == "__main__":
    main()
