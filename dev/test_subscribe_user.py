#!/usr/bin/env python3

import requests
import json
import time
import threading
from datetime import datetime

# Test user subscription endpoint
print("Testing /subscribe/user endpoint...")

def test_user_subscription(base_url, user_id, timeout=30):
    """Test user subscription with long polling"""
    print(f"\n🔔 Starting long-poll subscription for user {user_id}")
    print(f"⏰ Waiting for notifications (timeout: {timeout}s)...")
    
    try:
        url = f"{base_url}/subscribe/user?user_id={user_id}"
        print(f"📡 GET {url}")
        
        start_time = datetime.now()
        response = requests.get(url, timeout=timeout + 5)  # Add buffer to request timeout
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"⏱️  Response received after {duration:.1f} seconds")
        print(f"📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                response_json = response.json()
                print(f"✅ Notification received!")
                print(f"📨 Response: {json.dumps(response_json, indent=2)}")
                
                if response_json.get('change'):
                    print(f"🔔 Change detected in group: {response_json.get('notified_group', 'unknown')}")
                    print(f"👥 User groups: {response_json.get('user_groups', [])}")
                else:
                    print("ℹ️  Status update without specific change")
                    
            except json.JSONDecodeError:
                print(f"📄 Raw response: {response.text}")
                
        elif response.status_code == 204:
            print(f"⏰ Long-poll timeout - No changes detected")
            
        elif response.status_code == 400:
            print(f"❌ Bad request: {response.text}")
            
        else:
            print(f"❓ Unexpected status: {response.text}")
            
    except requests.exceptions.Timeout:
        print(f"⏰ Request timeout after {timeout + 5}s")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")

def send_test_message(base_url, user_id, group_id, content):
    """Send a test message to trigger notifications"""
    print(f"\n📤 Sending test message...")
    
    try:
        url = f"{base_url}/messages"
        headers = {'Content-Type': 'application/json'}
        data = {
            "userId": user_id,
            "groupId": group_id, 
            "content": content
        }
        
        print(f"📡 POST {url}")
        print(f"📝 Message: {content}")
        
        response = requests.post(url, json=data, headers=headers, timeout=10)
        print(f"📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"✅ Message sent successfully!")
        else:
            print(f"❌ Failed to send message: {response.text}")
            
    except Exception as e:
        print(f"❌ Error sending message: {e}")

def trigger_manual_notification(base_url, group_name):
    """Manually trigger a notification for testing"""
    print(f"\n🔔 Manually triggering notification for group '{group_name}'...")
    
    try:
        url = f"{base_url}/notify/{group_name}"
        response = requests.post(url, timeout=10)
        print(f"📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"✅ Notification triggered successfully!")
        else:
            print(f"❌ Failed to trigger notification: {response.text}")
            
    except Exception as e:
        print(f"❌ Error triggering notification: {e}")

def demo_subscription_workflow(base_url):
    """Demonstrate the complete subscription workflow"""
    print("\n" + "="*60)
    print("🚀 SUBSCRIPTION WORKFLOW DEMO")
    print("="*60)
    
    # Step 1: Login/create user
    print("\n1️⃣  Creating/logging in user...")
    try:
        login_response = requests.post(
            f"{base_url}/login",
            json={"username": "testuser"},
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        if login_response.status_code == 200:
            user_data = login_response.json()
            user_id = user_data['user_id']
            print(f"✅ User ID: {user_id}")
            if user_data.get('created'):
                print("🆕 New user created")
            else:
                print("👤 Existing user found")
        else:
            print(f"❌ Login failed: {login_response.text}")
            return
    except Exception as e:
        print(f"❌ Login error: {e}")
        return
    
    # Step 2: Start subscription in background
    print(f"\n2️⃣  Starting subscription for user {user_id}...")
    subscription_thread = threading.Thread(
        target=test_user_subscription,
        args=(base_url, user_id, 60),  # 60 second timeout
        name="SubscriptionThread"
    )
    subscription_thread.daemon = True
    subscription_thread.start()
    
    # Step 3: Wait a bit then trigger some events
    print("\n3️⃣  Waiting 5 seconds before triggering events...")
    time.sleep(5)
    
    # Step 4: Trigger notifications
    print("\n4️⃣  Triggering test events...")
    
    # Try to send a message (this might fail if no groups exist)
    send_test_message(base_url, user_id, 1, f"Test message at {datetime.now()}")
    
    time.sleep(2)
    
    # Manual notification trigger
    trigger_manual_notification(base_url, "default")
    
    time.sleep(2)
    trigger_manual_notification(base_url, "general")
    
    # Step 5: Wait for subscription to complete
    print(f"\n5️⃣  Waiting for subscription to complete...")
    subscription_thread.join(timeout=70)
    
    print("\n✅ Demo completed!")

# Test local server
print("=" * 60)
print("TESTING LOCAL SERVER")
print("=" * 60)

local_base_url = "http://localhost:8080"

# Simple subscription test
print("\n🧪 Simple subscription test (10 second timeout):")
test_user_subscription(local_base_url, "123", 10)

# Full workflow demo
demo_subscription_workflow(local_base_url)

print("\n" + "=" * 60)
print("TESTING REMOTE SERVER")
print("=" * 60)

remote_base_url = "https://bondy-backend-python-mi3a.onrender.com"

# Simple subscription test  
print("\n🧪 Simple subscription test (10 second timeout):")
test_user_subscription(remote_base_url, "123", 10)

# Full workflow demo
demo_subscription_workflow(remote_base_url)

print("\n" + "=" * 60)
print("🏁 ALL TESTS COMPLETED")
print("=" * 60)
print("\n💡 How to test manually:")
print("1. Run this script")
print("2. In another terminal, send a POST request to trigger notifications:")
print(f"   curl -X POST {local_base_url}/notify/default")
print("3. Or send a message:")
print(f'   curl -X POST {local_base_url}/messages -H "Content-Type: application/json" -d \'{{"userId":1,"groupId":1,"content":"Hello"}}\'')
