# Chat Backend API Documentation

This document describes the RESTful API endpoints for the Python chat backend server.

## Base URL
```
http://127.0.0.1:8080
```

## CORS Support
All endpoints support CORS with the following headers:
- `Access-Control-Allow-Origin: *`
- `Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS`
- `Access-Control-Allow-Headers: Content-Type, Authorization`

## Authentication
Currently, the API uses simple user IDs for authentication. No bearer tokens or complex auth is implemented.

---

## Endpoints

### 1. User Management

#### POST /login
Create a new user or login an existing user.

**Request Body:**
```json
{
    "username": "string (required)"
}
```

**Response:**
```json
{
    "user_id": 123,
    "username": "john_doe",
    "created": true
}
```

**Status Codes:**
- `200 OK` - Success
- `400 Bad Request` - Missing username

---

### 2. Chat Group Management

#### POST /create-chat
Create a new chat group.

**Request Body:**
```json
{
    "groupName": "string (required)",
    "creatorId": "number (required)",
    "members": ["username1", "username2"] // optional array of usernames
}
```

**Response:**
```json
{
    "group_id": 456,
    "group_name": "My New Group",
    "creator_id": 123,
    "members": [
        {
            "id": 123,
            "username": "john_doe"
        },
        {
            "id": 124,
            "username": "jane_smith"
        }
    ],
    "warning": "Users not found: nonexistent_user" // optional, if some members weren't found
}
```

**Features:**
- The creator is automatically added as the first member
- If `members` array is provided, those users will be added to the group during creation
- Users that don't exist will be ignored, but a warning will be included in the response
- Creator username in the members list will be ignored (no duplicates)

**Status Codes:**
- `200 OK` - Group created successfully
- `400 Bad Request` - Missing required fields
- `404 Not Found` - Creator user not found
- `409 Conflict` - Group name already exists

#### GET /chats
Get all chat groups for a user.

**Query Parameters:**
- `userId` (required) - The user ID

**Example:**
```
GET /chats?userId=123
```

**Response:**
```json
{
    "user_id": 123,
    "chats": [
        {
            "id": 456,
            "name": "General Chat",
            "members": [
                {
                    "id": 123,
                    "username": "john_doe"
                },
                {
                    "id": 124,
                    "username": "jane_smith"
                }
            ]
        },
        {
            "id": 789,
            "name": "Project Team",
            "members": [
                {
                    "id": 123,
                    "username": "john_doe"
                },
                {
                    "id": 125,
                    "username": "bob_wilson"
                }
            ]
        }
    ]
}
```

#### POST /add-user-to-group
Add a user to an existing group.

**Request Body:**
```json
{
    "groupId": "number (required)",
    "userId": "number (required)"
}
```

**Response:**
```json
{
    "message": "User added to group successfully"
}
```

#### GET /group-users
Get all users in a specific group.

**Query Parameters:**
- `groupId` (required) - The group ID

**Example:**
```
GET /group-users?groupId=456
```

**Response:**
```json
[
    {
        "id": 123,
        "username": "john_doe"
    },
    {
        "id": 124,
        "username": "jane_smith"
    }
]
```

---

### 3. Messaging

#### POST /send
Send a message to a chat group.

**Request Body:**
```json
{
    "text": "string (required)",
    "user_id": "number (required)",
    "chat_id": "number (required)"
}
```

**Response:**
```json
{
    "message": "Message sent",
    "message_id": 789
}
```

#### GET /messages
Get messages from a specific chat.

**Query Parameters:**
- `chatId` (required) - The chat/group ID

**Example:**
```
GET /messages?chatId=456
```

**Response:**
```json
[
    {
        "id": 789,
        "text": "Hello everyone!",
        "user_id": 123,
        "username": "john_doe",
        "chat_id": 456,
        "timestamp": "2024-01-15T10:30:00"
    }
]
```

#### DELETE /messages
Delete all messages (admin function).

**Request Body:**
```json
{
    "confirm": true
}
```

---

### 4. Real-time Notifications

#### GET /subscribe/user
Long-polling endpoint for real-time notifications.

**Query Parameters:**
- `userId` (required) - The user ID to subscribe to

**Example:**
```
GET /subscribe/user?userId=123
```

**Response:**
When a notification is available:
```json
{
    "type": "group_change",
    "group_id": 456,
    "message": "New message in group"
}
```

**Behavior:**
- Connection stays open for up to 30 seconds waiting for notifications
- Returns immediately if there are pending notifications
- Clients should reconnect after receiving a response or timeout

---

## Error Responses

All endpoints return error responses in the following format:

```json
{
    "error": "Description of the error"
}
```

Common status codes:
- `400 Bad Request` - Invalid request data
- `404 Not Found` - Resource not found
- `409 Conflict` - Resource already exists
- `500 Internal Server Error` - Server error

---

## Usage Examples

### JavaScript/Fetch API

```javascript
// Login/Create user
const loginResponse = await fetch('http://127.0.0.1:8080/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'john_doe' })
});
const userData = await loginResponse.json();

// Create chat group with members
const createChatResponse = await fetch('http://127.0.0.1:8080/create-chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        groupName: 'My New Group',
        creatorId: userData.user_id,
        members: ['jane_doe', 'bob_smith'] // optional
    })
});
const groupData = await createChatResponse.json();

// Get user's chats
const chatsResponse = await fetch(`http://127.0.0.1:8080/chats?userId=${userData.user_id}`);
const chats = await chatsResponse.json();

// Send message
const messageResponse = await fetch('http://127.0.0.1:8080/send', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        text: 'Hello everyone!',
        user_id: userData.user_id,
        chat_id: groupData.group_id
    })
});

// Subscribe to notifications (long-polling)
const subscribeResponse = await fetch(`http://127.0.0.1:8080/subscribe/user?userId=${userData.user_id}`);
const notification = await subscribeResponse.json();
```

### cURL Examples

```bash
# Login/Create user
curl -X POST http://127.0.0.1:8080/login \
  -H "Content-Type: application/json" \
  -d '{"username": "john_doe"}'

# Create chat group with members
curl -X POST http://127.0.0.1:8080/create-chat \
  -H "Content-Type: application/json" \
  -d '{"groupName": "My New Group", "creatorId": 123, "members": ["jane_doe", "bob_smith"]}'

# Get user's chats
curl "http://127.0.0.1:8080/chats?userId=123"

# Send message
curl -X POST http://127.0.0.1:8080/send \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello!", "user_id": 123, "chat_id": 456}'

# Subscribe to notifications
curl "http://127.0.0.1:8080/subscribe/user?userId=123"
```

---

## Testing

Run the test suite to verify all endpoints:

```bash
cd dev/
python run_all_tests.py
```

Individual test files:
- `test_login.py` - Login endpoint tests
- `test_create_chat.py` - Chat creation tests
- `test_chat_integration.py` - Full integration tests
- `test_cors.py` - CORS functionality tests
- `test_get_endpoints.py` - GET endpoint tests
- `test_subscribe_user.py` - Notification tests

---

## Frontend Integration

See `dev/chat_frontend_example.html` for a complete frontend example showing how to integrate with all the API endpoints.
