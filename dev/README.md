# API Testing Suite

This directory contains comprehensive tests for the Bondy Python Backend API.

## Test Files

### 1. `test_basic.py` - Basic Endpoints & System Control
Tests the fundamental server endpoints:
- **GET /** - Root endpoint
- **GET /health** - Health check
- **GET /groups** - List active groups  
- **GET /users** - List all users
- **POST /fall** - Set system down
- **POST /revive** - Revive system

### 2. `test_user_groups.py` - User-Group Management
Tests user and group management functionality:
- Adding users to groups individually
- Setting all groups for a user at once
- Getting user's groups
- Removing users from groups
- Listing all users and their groups

### 3. `test_notifications.py` - Long-Polling & Notifications  
Tests the real-time notification system:
- Group-specific long-polling
- User-based long-polling (multi-group)
- Notification triggers for specific groups
- Notification triggers for all groups
- Timeout behavior

### 4. `test_edge_cases.py` - Error Conditions & Edge Cases
Tests error handling and edge cases:
- Invalid endpoints
- Invalid HTTP methods
- Invalid JSON payloads
- Missing query parameters
- Special characters in names
- System down behavior

### 5. `run_all_tests.py` - Test Runner
Runs all test files in sequence with nice formatting.

## Usage

### Run All Tests
```bash
python dev/run_all_tests.py
```

### Run Individual Tests
```bash
# Basic functionality
python dev/test_basic.py

# User-group management
python dev/test_user_groups.py

# Notifications and long-polling
python dev/test_notifications.py

# Error conditions
python dev/test_edge_cases.py
```

### Local vs Remote Testing

Each test file has a `BASE_URL` configuration at the top:

```python
# For remote testing (default)
BASE_URL = "https://bondy-backend-python-mi3a.onrender.com"

# For local testing (uncomment this line)
# BASE_URL = "http://localhost:8083"
```

## Example Scenarios Tested

### User-Group Management Flow
1. Set up users: alice, bob, charlie
2. Add users to groups: frontend, backend, admin, notifications
3. Check individual user groups
4. Bulk update user groups
5. Remove users from specific groups

### Long-Polling Flow
1. Set up users with groups
2. Start background long-polling threads
3. Send notifications to specific groups
4. Verify long-polling clients receive notifications
5. Test timeout behavior

### Error Handling
1. Invalid endpoints return 404
2. Invalid methods return appropriate errors  
3. Malformed JSON returns 400
4. System down blocks non-essential endpoints
5. Control endpoints work even when system is down

## Expected Behavior

### Successful Responses
- **200 OK** - Normal successful responses
- **204 No Content** - Long-polling timeout (no notifications)

### Error Responses  
- **400 Bad Request** - Invalid JSON, missing parameters
- **404 Not Found** - Invalid endpoints, unknown users
- **503 Service Unavailable** - System is down

### Long-Polling
- Clients wait up to 25 seconds for notifications
- Returns immediately when notifications are sent
- Returns 204 after timeout if no notifications

## Tips

1. **Long-polling tests** may take 25+ seconds to complete due to timeouts
2. **System control tests** change the server state - health checks will reflect this
3. **Notification tests** use background threads - watch for `[Thread]` prefixed output  
4. **Error tests** are expected to return 4xx/5xx status codes - this is normal
5. **Local testing** requires your server to be running on localhost:8083
