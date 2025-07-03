#!/usr/bin/env python3

import subprocess
import sys
import time

def run_test_file(test_file, description):
    """Run a test file and show results"""
    print("\n" + "=" * 60)
    print(f"RUNNING: {description}")
    print("=" * 60)
    
    try:
        # Run the test file
        result = subprocess.run(
            [sys.executable, test_file], 
            capture_output=False,  # Show output in real-time
            text=True,
            cwd="."
        )
        
        if result.returncode == 0:
            print(f"\n✅ {description} completed successfully")
        else:
            print(f"\n❌ {description} failed with exit code {result.returncode}")
            
    except Exception as e:
        print(f"\n❌ Error running {description}: {e}")
    
    # Wait a bit between tests
    time.sleep(2)

def main():
    """Run all test files in sequence"""
    print("🚀 STARTING COMPREHENSIVE API TESTS")
    print("=" * 60)
    
    # List of test files and their descriptions
    test_files = [
        ("dev/test_basic.py", "Basic Endpoints & System Control"),
        ("dev/test_user_groups.py", "User-Group Management"), 
        ("dev/test_notifications.py", "Long-Polling & Notifications"),
        ("dev/test_edge_cases.py", "Error Conditions & Edge Cases"),
    ]
    
    # Run each test file
    for test_file, description in test_files:
        run_test_file(test_file, description)
    
    print("\n" + "=" * 60)
    print("🎉 ALL TESTS COMPLETED!")
    print("=" * 60)
    print("\nIf you want to run individual tests:")
    for test_file, description in test_files:
        print(f"  python {test_file}  # {description}")
    
    print(f"\nTo switch to local testing, edit the BASE_URL in each test file:")
    print(f"  Change: BASE_URL = \"https://bondy-backend-python-mi3a.onrender.com\"")
    print(f"  To:     BASE_URL = \"http://localhost:8083\"")

if __name__ == "__main__":
    main()
