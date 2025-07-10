#!/usr/bin/env python3

import requests
import json
import time
import threading
from datetime import datetime

# Test user subscription endpoint
print("Testing /subscribe/user endpoint...")
 

 
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
        
        response = requests.post(url, json=data, headers=headers)
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
            json={"username": "emily"},
            headers={'Content-Type': 'application/json'}, 
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
    
    # Step 2: Start subscription in background with result container
    print(f"\n2️⃣  Starting subscription for user {user_id}...")
    
    
    
    response = requests.get(base_url + '/subscribe/user?user_id=' + str(user_id),  )
   
    if response.status_code == 200:
        print("✅ Subscription started successfully!")
        subscription_result = response.json()
        print('subscription_result', subscription_result)
    else:
        print(f"❌ Failed to start subscription: {response.text}") 
        
    
    # Step 6: Display subscription results
    
    print("\n✅ Demo completed!")

# Test local server 
print("TESTING LOCAL SERVER") 

local_base_url = "http://localhost:8082"

local_base_url = 'https://bondy-backend-python-mi3a.onrender.com'
# Simple subscription test with result capture 
#simple_result = test_user_subscription(local_base_url, "7", 10)
#print(f"\n📋 Simple Test Result Summary:")
#print(f"   Status: {simple_result.get('status', 'unknown')}")
#print(f"   Duration: {simple_result.get('duration', 'unknown')} seconds")
#if simple_result.get('response'):
#    print(f"   Response: {simple_result['response']}")

# Full workflow demo
demo_subscription_workflow(local_base_url)

#print("\n" + "=" * 60)
print("TESTING REMOTE SERVER")
#print("=" * 60)

remote_base_url = None #"https://bondy-backend-python-mi3a.onrender.com"

if remote_base_url is None:
    print("❌ Remote server URL not set. Skipping remote tests.")
else:
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
