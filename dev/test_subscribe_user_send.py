#!/usr/bin/env python3

import requests
import json
import time
import threading
from datetime import datetime

# Test user subscription endpoint
print("Testing /subscribe/user endpoint...")

def test_user_subscription(base_url, user_id, timeout=30, result_container=None):
    """Test user subscription with long polling"""
    print(f"\n🔔 Starting long-poll subscription for user {user_id}")
    print(f"⏰ Waiting for notifications (timeout: {timeout}s)...")
    
    result = {"status": "started", "response": None, "error": None}
    if result_container is not None:
        result_container.clear()
        result_container.append(result)
    
    try:
        url = f"{base_url}/subscribe/user?user_id={user_id}"
        print(f"📡 GET {url}")
        
        start_time = datetime.now()
        response = requests.get(url, timeout=timeout + 5)  # Add buffer to request timeout
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"⏱️  Response received after {duration:.1f} seconds")
        print(f"📊 Status: {response.status_code}")
        
        result["status"] = "completed"
        result["duration"] = duration
        result["status_code"] = response.status_code
        
        if response.status_code == 200:
            try:
                response_json = response.json()
                result["response"] = response_json
                print(f"✅ Notification received!")
                print(f"📨 Response: {json.dumps(response_json, indent=2)}")
                
                if response_json.get('change'):
                    print(f"🔔 Change detected in group: {response_json.get('notified_group', 'unknown')}")
                    print(f"👥 User groups: {response_json.get('user_groups', [])}")
                else:
                    print("ℹ️  Status update without specific change")
                    
            except json.JSONDecodeError:
                result["response"] = response.text
                print(f"📄 Raw response: {response.text}")
                
        elif response.status_code == 204:
            print(f"⏰ Long-poll timeout - No changes detected")
            result["response"] = "timeout"
            
        elif response.status_code == 400:
            print(f"❌ Bad request: {response.text}")
            result["response"] = response.text
            
        else:
            print(f"❓ Unexpected status: {response.text}")
            result["response"] = response.text
            
    except requests.exceptions.Timeout:
        error_msg = f"Request timeout after {timeout + 5}s"
        print(f"⏰ {error_msg}")
        result["status"] = "timeout"
        result["error"] = error_msg
    except requests.exceptions.RequestException as e:
        error_msg = f"Request error: {e}"
        print(f"❌ Error: {e}")
        result["status"] = "error"
        result["error"] = error_msg
    
    if result_container is not None:
        result_container[0] = result
    
    return result

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
            json={"username": "anna", 'password': 'test123'},
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
    
    
    # Step 4: Trigger notifications
    print("\n4️⃣  Triggering test events...")
    
    # Try to send a message (this might fail if no groups exist)
    send_test_message(base_url, user_id, 7, f"Test message at {datetime.now()}")
    
    time.sleep(2)
     
     
    print("\n✅ Demo completed!")

# Test local server 

local_base_url = "http://localhost:8082"

local_base_url = 'https://bondy-backend-python-mi3a.onrender.com'
 
# Full workflow demo
demo_subscription_workflow(local_base_url)
 