# Group-based Notification System with User Management

This document explains the enhanced notification system that supports multiple groups for targeted notifications, with special support for users who belong to multiple groups.

## Overview

The system now supports:
1. **Multiple condition variables** - each associated with a specific group
2. **User-group memberships** - users can belong to multiple groups
3. **User-based subscriptions** - single subscription that listens to all of a user's groups
4. **Targeted notifications** - notify specific groups or all groups

This allows for efficient notification management where users can subscribe once and receive notifications from any group they belong to.

## Key Features

### 1. Group-based Subscriptions (Single Group)
Clients can subscribe to notifications for specific groups using query parameters:
```
GET /subscribe/status?group=group1
GET /subscribe/status?group=myapp
GET /subscribe/status  # defaults to "default" group
```

### 2. User-based Subscriptions (Multiple Groups)
**NEW**: Users can subscribe to all their groups with a single request:
```
GET /subscribe/user?user_id=alice  # Listens to ALL groups that alice belongs to
```

### 3. Targeted Notifications
Send notifications to specific groups:
```
POST /notify/group1     # Notify only group1 subscribers
POST /notify/myapp      # Notify only myapp subscribers  
POST /notify/all        # Notify all groups
```

### 4. User-Group Management
Manage which groups users belong to:
```
GET /users                           # List all users and their groups
GET /user/{user_id}/groups          # Get groups for specific user
POST /user/{user_id}/groups         # Set all groups for a user (JSON body)
POST /user/{user_id}/groups/{group} # Add user to a group
DELETE /user/{user_id}/groups/{group} # Remove user from a group
```

## API Endpoints

### Subscribe to Group Notifications (Single Group)
- **Endpoint**: `GET /subscribe/status?group={group_name}`
- **Parameters**: 
  - `group`: (optional) Group name to subscribe to. Defaults to "default"
- **Response**: 
  - `200`: State change notification with current status
  - `204`: No changes within timeout period (25 seconds)

**Example Response (200)**:
```json
{
  "status": "alive",
  "active": true,
  "change": true,
  "group": "group1"
}
```

### Subscribe to User Notifications (Multiple Groups)
- **Endpoint**: `GET /subscribe/user?user_id={user_id}`
- **Parameters**: 
  - `user_id`: (required) User ID to subscribe for
- **Response**: 
  - `200`: State change notification when ANY of the user's groups is notified
  - `204`: No changes within timeout period (25 seconds)
  - `400`: Missing or invalid user_id

**Example Response (200)**:
```json
{
  "status": "alive",
  "active": true,
  "change": true,
  "user_id": "alice",
  "notified_group": "frontend",
  "user_groups": ["frontend", "notifications", "admin"]
}
```

### Send Group Notification
- **Endpoint**: `POST /notify/{group_name}`
- **Parameters**:
  - `group_name`: Name of the group to notify, or "all" for all groups
- **Response**: Confirmation message

**Example Response**:
```json
{
  "message": "notification sent to group group1"
}
```

### User-Group Management

#### List All Users
- **Endpoint**: `GET /users`
- **Response**: All users and their group memberships

**Example Response**:
```json
{
  "user_groups": {
    "alice": ["frontend", "notifications", "admin"],
    "bob": ["backend", "notifications"]
  },
  "user_count": 2
}
```

#### Get User's Groups
- **Endpoint**: `GET /user/{user_id}/groups`
- **Response**: Groups that the user belongs to

**Example Response**:
```json
{
  "user_id": "alice",
  "groups": ["frontend", "notifications", "admin"]
}
```

#### Set User's Groups (Replace All)
- **Endpoint**: `POST /user/{user_id}/groups`
- **Body**: JSON with groups array
- **Response**: Confirmation with updated groups

**Example Request**:
```json
{
  "groups": ["frontend", "notifications", "admin"]
}
```

**Example Response**:
```json
{
  "user_id": "alice",
  "groups": ["frontend", "notifications", "admin"],
  "message": "groups updated"
}
```

#### Add User to Group
- **Endpoint**: `POST /user/{user_id}/groups/{group_name}`
- **Response**: Confirmation with all user's groups

**Example Response**:
```json
{
  "user_id": "alice",
  "added_to_group": "newgroup",
  "all_groups": ["frontend", "notifications", "admin", "newgroup"]
}
```

#### Remove User from Group
- **Endpoint**: `DELETE /user/{user_id}/groups/{group_name}`
- **Response**: Confirmation with remaining groups

**Example Response**:
```json
{
  "user_id": "alice",
  "removed_from_group": "admin",
  "remaining_groups": ["frontend", "notifications"]
}
```

### List Active Groups
- **Endpoint**: `GET /groups`
- **Response**: List of currently active groups

**Example Response**:
```json
{
  "active_groups": ["default", "group1", "group2"],
  "count": 3
}
```

## Implementation Details

### Thread Safety
- Each group has its own `threading.Condition` variable
- All condition variables share the same lock (`state_lock`) for consistent state access
- The `group_conditions` dictionary is protected by `group_conditions_lock`
- User-group mappings are protected by `user_groups_lock`

### User-Group Subscription Logic
- When a user subscribes via `/subscribe/user`, the system:
  1. Gets all groups the user belongs to
  2. Creates condition variables for each group if they don't exist
  3. Starts separate threads to wait on each group's condition
  4. Returns immediately when ANY group is notified
  5. Cleans up waiting threads after notification or timeout

### Group Lifecycle
- Groups are created automatically when first accessed
- Groups persist until the server restarts
- User-group memberships persist until explicitly changed or server restarts
- No automatic cleanup of empty groups (this could be added as an enhancement)

### Backwards Compatibility
- Existing `/subscribe/status` calls without group parameter default to "default" group
- All existing functionality remains unchanged
- New user-based endpoints are additive

## Usage Examples

### User-based Multi-Group Subscription (Recommended)
```python
import requests

# First, set up user's groups
requests.post("http://localhost:8083/user/alice/groups", 
              json={"groups": ["frontend", "notifications", "admin"]})

# Subscribe to ALL of alice's groups with a single request
response = requests.get("http://localhost:8083/subscribe/user?user_id=alice", timeout=30)
if response.status_code == 200:
    notification = response.json()
    print(f"User {notification['user_id']} got notification from group {notification['notified_group']}")
    print(f"User belongs to groups: {notification['user_groups']}")
```

### Basic Group Subscription (Single Group)
```python
import requests

# Subscribe to a specific group
response = requests.get("http://localhost:8083/subscribe/status?group=myapp", timeout=30)
if response.status_code == 200:
    notification = response.json()
    print(f"Received notification for group {notification['group']}")
```

### User-Group Management
```python
import requests

# Set user's groups (replaces all existing groups)
response = requests.post("http://localhost:8083/user/alice/groups", 
                        json={"groups": ["frontend", "backend", "admin"]})

# Add user to additional group
response = requests.post("http://localhost:8083/user/alice/groups/notifications")

# Remove user from a group
response = requests.delete("http://localhost:8083/user/alice/groups/backend")

# Check user's current groups
response = requests.get("http://localhost:8083/user/alice/groups")
print(response.json())  # {"user_id": "alice", "groups": ["frontend", "admin", "notifications"]}
```

### Sending Targeted Notifications
```python
import requests

# Notify specific group (all users in that group will be notified)
response = requests.post("http://localhost:8083/notify/frontend")
print(response.json())  # {"message": "notification sent to group frontend"}

# Notify all groups
response = requests.post("http://localhost:8083/notify/all") 
print(response.json())  # {"message": "notification sent to all groups"}
```

### Real-world Example: Chat Application
```python
import requests
import threading

# Set up users for a chat application
users_setup = {
    "alice": ["general", "frontend-team", "announcements"],
    "bob": ["general", "backend-team", "announcements"], 
    "charlie": ["general", "frontend-team", "backend-team", "admin"]
}

# Set up all users
for user_id, groups in users_setup.items():
    requests.post(f"http://localhost:8083/user/{user_id}/groups", 
                  json={"groups": groups})

# Each user subscribes to their groups
def user_subscription(user_id):
    while True:
        try:
            response = requests.get(f"http://localhost:8083/subscribe/user?user_id={user_id}", 
                                  timeout=30)
            if response.status_code == 200:
                data = response.json()
                print(f"[{user_id}] Notification from {data['notified_group']}: {data}")
                # Process the notification...
        except requests.exceptions.Timeout:
            # Normal timeout, continue listening
            continue
        except Exception as e:
            print(f"[{user_id}] Error: {e}")
            break

# Start user subscriptions
for user_id in users_setup.keys():
    thread = threading.Thread(target=user_subscription, args=(user_id,))
    thread.daemon = True
    thread.start()

# Send notifications to different groups
requests.post("http://localhost:8083/notify/announcements")  # All users notified
requests.post("http://localhost:8083/notify/frontend-team")  # Alice and Charlie notified
requests.post("http://localhost:8083/notify/admin")          # Only Charlie notified
```

### JavaScript Example
```javascript
// Subscribe to group notifications
async function subscribeToGroup(groupName) {
    try {
        const response = await fetch(`/subscribe/status?group=${groupName}`, {
            method: 'GET',
            timeout: 25000
        });
        
        if (response.status === 200) {
            const data = await response.json();
            console.log(`Notification for ${groupName}:`, data);
        } else if (response.status === 204) {
            console.log(`No changes for ${groupName}`);
        }
    } catch (error) {
        console.error(`Error subscribing to ${groupName}:`, error);
    }
}

// Send notification to group
async function notifyGroup(groupName) {
    try {
        const response = await fetch(`/notify/${groupName}`, {
            method: 'POST'
        });
        const result = await response.json();
        console.log(result.message);
    } catch (error) {
        console.error(`Error notifying ${groupName}:`, error);
    }
}
```

## Testing

Use the provided test scripts to test the functionality:

### Test User-based Multi-Group Subscriptions:
```bash
python test_user_groups.py
```

This script will:
1. Set up multiple users with different group memberships
2. Start user-based subscriptions (each user listens to ALL their groups)
3. Send targeted notifications to specific groups
4. Demonstrate how only relevant users get notified
5. Show dynamic group membership changes

### Test Basic Group Functionality:
```bash
python test_groups.py
```

This script demonstrates the original group-based functionality.

## Migration Notes

If you have existing code using the notification system:

1. **No changes required** for basic functionality
2. **Recommended**: Use `/subscribe/user?user_id={user_id}` instead of multiple `/subscribe/status?group={group}` calls
3. **Set up user-group memberships** using the new user management endpoints
4. **Optional**: Use `/notify/{group}` instead of triggering state changes for more precise control

### Migration Steps:
1. **Identify your users and their group memberships**
2. **Set up user-group mappings** using `POST /user/{user_id}/groups`
3. **Replace multiple group subscriptions** with single user subscriptions
4. **Update notification logic** to use group-targeted notifications

### Before (Multiple Subscriptions):
```python
# Old way - multiple subscriptions per user
def subscribe_to_multiple_groups(groups):
    threads = []
    for group in groups:
        thread = threading.Thread(target=subscribe_to_group, args=(group,))
        thread.start()
        threads.append(thread)
    return threads

subscribe_to_multiple_groups(["frontend", "notifications", "admin"])
```

### After (Single User Subscription):
```python
# New way - single subscription for all user's groups
requests.post("http://localhost:8083/user/alice/groups", 
              json={"groups": ["frontend", "notifications", "admin"]})

def subscribe_as_user(user_id):
    response = requests.get(f"http://localhost:8083/subscribe/user?user_id={user_id}", timeout=30)
    # Handle notification from ANY of the user's groups
    return response

subscribe_as_user("alice")
```

## Future Enhancements

Potential improvements that could be added:
- **Group cleanup** for unused groups and users
- **Group-based authentication/authorization** 
- **Metrics** for group usage and user activity
- **Group-specific configuration** options (e.g., different timeout values)
- **Persistent storage** for user-group memberships (database integration)
- **Group hierarchies** (parent/child group relationships)
- **Real-time user presence** tracking within groups
- **Message history** and replay functionality for groups
- **Rate limiting** per group or user
- **WebSocket support** for real-time bidirectional communication

## Performance Considerations

### Scalability
- **Memory usage**: Each group creates a condition variable. Each user-group membership uses minimal memory.
- **Thread usage**: User subscriptions create temporary threads (one per group the user belongs to), but these are short-lived.
- **Network efficiency**: Single user subscription replaces multiple group subscriptions, reducing network overhead.

### Recommendations for Production
- **Limit maximum groups per user** to prevent excessive thread creation
- **Implement group cleanup** to remove unused groups
- **Monitor active subscriptions** and implement connection limits
- **Consider WebSocket upgrades** for high-frequency notifications
- **Add persistence layer** for user-group mappings to survive server restarts

### Current Limitations
- User-group memberships are lost on server restart
- No built-in authentication or authorization
- No rate limiting on subscriptions or notifications
- Thread-based waiting may not scale to thousands of concurrent users
