#!/usr/bin/env python3

import requests
import json

def test_cors_headers(base_url):
    """Test CORS headers on various endpoints"""
    print(f"\n🌐 Testing CORS headers for {base_url}")
    print("=" * 60)
    
    endpoints_to_test = [
        ('/health', 'GET'),
        ('/login', 'POST'),
        ('/messages', 'POST'),
        ('/chats', 'GET'),
        ('/', 'GET'),
        ('/health', 'OPTIONS'),  # Preflight request
        ('/login', 'OPTIONS'),   # Preflight request
    ]
    
    for endpoint, method in endpoints_to_test:
        print(f"\n🔍 Testing {method} {endpoint}")
        
        try:
            if method == 'GET':
                response = requests.get(f"{base_url}{endpoint}", timeout=10)
            elif method == 'POST':
                if endpoint == '/login':
                    data = {"username": "testuser"}
                    response = requests.post(
                        f"{base_url}{endpoint}", 
                        json=data,
                        headers={'Content-Type': 'application/json'},
                        timeout=10
                    )
                elif endpoint == '/messages':
                    data = {"userId": 1, "groupId": 1, "content": "test"}
                    response = requests.post(
                        f"{base_url}{endpoint}", 
                        json=data,
                        headers={'Content-Type': 'application/json'},
                        timeout=10
                    )
                else:
                    response = requests.post(f"{base_url}{endpoint}", timeout=10)
            elif method == 'OPTIONS':
                response = requests.options(f"{base_url}{endpoint}", timeout=10)
            
            print(f"📊 Status: {response.status_code}")
            
            # Check CORS headers
            cors_headers = {
                'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
                'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
                'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
                'Access-Control-Max-Age': response.headers.get('Access-Control-Max-Age'),
            }
            
            print("🔒 CORS Headers:")
            for header, value in cors_headers.items():
                if value:
                    print(f"  ✅ {header}: {value}")
                else:
                    print(f"  ❌ {header}: Missing")
            
            # Check if all required CORS headers are present
            required_headers = ['Access-Control-Allow-Origin', 'Access-Control-Allow-Methods', 'Access-Control-Allow-Headers']
            missing_headers = [h for h in required_headers if not cors_headers[h.replace('-', '_').lower()]]
            
            if not missing_headers:
                print("  🎉 All required CORS headers present!")
            else:
                print(f"  ⚠️  Missing headers: {missing_headers}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error: {e}")
        
        print("-" * 40)

def test_browser_like_request(base_url):
    """Test a browser-like CORS request with preflight"""
    print(f"\n🌍 Testing Browser-like CORS Request Flow")
    print("=" * 60)
    
    # Step 1: Preflight request (OPTIONS)
    print("\n1️⃣  Sending preflight OPTIONS request...")
    try:
        preflight_headers = {
            'Origin': 'http://localhost:3000',
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'Content-Type'
        }
        
        response = requests.options(
            f"{base_url}/login",
            headers=preflight_headers,
            timeout=10
        )
        
        print(f"📊 Preflight Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Preflight successful!")
            
            # Check if server allows the actual request
            allow_origin = response.headers.get('Access-Control-Allow-Origin')
            allow_methods = response.headers.get('Access-Control-Allow-Methods', '')
            allow_headers = response.headers.get('Access-Control-Allow-Headers', '')
            
            print(f"🔒 Server allows origin: {allow_origin}")
            print(f"🔒 Server allows methods: {allow_methods}")
            print(f"🔒 Server allows headers: {allow_headers}")
            
            if 'POST' in allow_methods and ('Content-Type' in allow_headers or '*' in allow_origin):
                print("✅ Server allows the actual POST request")
                
                # Step 2: Actual request
                print("\n2️⃣  Sending actual POST request...")
                actual_headers = {
                    'Origin': 'http://localhost:3000',
                    'Content-Type': 'application/json'
                }
                
                actual_response = requests.post(
                    f"{base_url}/login",
                    json={"username": "corstest"},
                    headers=actual_headers,
                    timeout=10
                )
                
                print(f"📊 Actual request status: {actual_response.status_code}")
                
                if actual_response.status_code in [200, 201]:
                    print("✅ Actual request successful!")
                    try:
                        print(f"📨 Response: {actual_response.json()}")
                    except:
                        print(f"📨 Response: {actual_response.text}")
                else:
                    print("❌ Actual request failed")
                    print(f"📨 Response: {actual_response.text}")
            else:
                print("❌ Server doesn't allow the POST request")
        else:
            print("❌ Preflight failed")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")

def create_test_html():
    """Create a simple HTML test page for manual CORS testing"""
    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>CORS Test</title>
</head>
<body>
    <h1>CORS Test Page</h1>
    <button onclick="testLogin()">Test Login</button>
    <button onclick="testHealth()">Test Health</button>
    <div id="result"></div>
    
    <script>
        const API_BASE = 'http://localhost:8080';  // Change this to your server URL
        
        async function testLogin() {
            try {
                const response = await fetch(API_BASE + '/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({username: 'testuser'})
                });
                
                const data = await response.json();
                document.getElementById('result').innerHTML = 
                    '<h3>Login Result:</h3><pre>' + JSON.stringify(data, null, 2) + '</pre>';
            } catch (error) {
                document.getElementById('result').innerHTML = 
                    '<h3>Login Error:</h3><pre>' + error.message + '</pre>';
            }
        }
        
        async function testHealth() {
            try {
                const response = await fetch(API_BASE + '/health');
                const data = await response.json();
                document.getElementById('result').innerHTML = 
                    '<h3>Health Result:</h3><pre>' + JSON.stringify(data, null, 2) + '</pre>';
            } catch (error) {
                document.getElementById('result').innerHTML = 
                    '<h3>Health Error:</h3><pre>' + error.message + '</pre>';
            }
        }
    </script>
</body>
</html>"""
    
    with open('test_cors.html', 'w') as f:
        f.write(html_content)
    
    print("📄 Created test_cors.html - Open this in a browser to test CORS manually")

# Test local server
print("🧪 CORS TESTING")
print("=" * 60)

local_base_url = "http://localhost:8080"

test_cors_headers(local_base_url)
test_browser_like_request(local_base_url)

# Test remote server
print("\n" + "=" * 60)
print("🌐 TESTING REMOTE SERVER")
print("=" * 60)

remote_base_url = "https://bondy-backend-python-mi3a.onrender.com"

test_cors_headers(remote_base_url)
test_browser_like_request(remote_base_url)

# Create test HTML file
print("\n" + "=" * 60)
print("📄 CREATING TEST HTML")
print("=" * 60)

create_test_html()

print("\n" + "=" * 60)
print("✅ CORS TESTING COMPLETED")
print("=" * 60)
print("\n💡 How to test manually:")
print("1. Open test_cors.html in a browser")
print("2. Check browser console for any CORS errors")
print("3. Click the test buttons to verify requests work")
print("4. If you see CORS errors, check that your server is running with the updated code")
