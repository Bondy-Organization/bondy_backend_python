#!/usr/bin/env python3
"""
Run all available tests for the chat backend
"""

import subprocess
import sys
import os
import time

def run_test(test_file, description):
    """Run a single test file"""
    print(f"\n{'='*60}")
    print(f"RUNNING: {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run([sys.executable, test_file], 
                              capture_output=False, 
                              text=True, 
                              cwd=os.path.dirname(os.path.abspath(__file__)))
        
        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
        else:
            print(f"❌ {description} - FAILED (exit code: {result.returncode})")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting comprehensive test suite for chat backend")
    print("Make sure the server is running on port 8080 before running tests!")
    
    input("\nPress Enter to continue, or Ctrl+C to abort...")
    
    tests = [
        ("dev/test_basic.py", "Basic Endpoints & System Control"),
        ("dev/test_user_groups.py", "User-Group Management"), 
        ("dev/test_notifications.py", "Long-Polling & Notifications"),
        ("dev/test_edge_cases.py", "Error Conditions & Edge Cases"),
        ("dev/test_create_chat.py", "Create chat endpoint tests"),
        ("dev/test_chat_integration.py", "Comprehensive chat integration tests"),
        ("dev/test_subscribe_user.py", "User subscription and notifications"),
        ("dev/test_cors.py", "CORS and preflight tests"),
        ("dev/test_get_endpoints.py", "GET endpoints with query parameters"),
    ]
    
    passed = 0
    total = 0
    
    for test_file, description in tests:
        if os.path.exists(test_file):
            total += 1
            if run_test(test_file, description):
                passed += 1
        else:
            print(f"⚠️  Test file {test_file} not found, skipping...")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Total tests run: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        return True
    else:
        print(f"❌ {total - passed} test(s) failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
