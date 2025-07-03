import os
import threading 
import requests
import socket # For raw socket programming
import json   # For handling JSON responses 
from database.database import SessionLocal, User, Grupo, Message, add_message
import time # Para um pequeno atraso
 
# --- Global State Variables ---
# These variables hold the system's operational status.
# A threading.Lock is used to ensure thread-safe access to these shared variables
# because both the HTTP server's client handlers (separate threads)
# and the SyncManager (separate thread) will be reading from and writing to them.
state_lock = threading.Lock()
_is_alive = True  # Indicates if the system is fundamentally operational
_is_active = os.getenv('IS_ACTIVE', 'false').lower() == 'true' # Active in a cluster
_peer_url = os.getenv('PEER_URL', None) # URL of a peer system for active/passive sync

# --- Event Notification Mechanism ---
# Dictionary to store condition variables for different groups
# Each group has its own condition variable for targeted notifications
group_conditions = {}
group_conditions_lock = threading.Lock()  # Protects the group_conditions dictionary

def get_or_create_group_condition(group_name):
    """
    Gets or creates a condition variable for a specific group.
    Thread-safe creation of condition variables.
    """
    with group_conditions_lock:
        if group_name not in group_conditions:
            group_conditions[group_name] = threading.Condition(state_lock)
        return group_conditions[group_name]

def get_active_groups():
    """
    Returns a list of currently active group names.
    Useful for debugging and monitoring.
    """
    with group_conditions_lock:
        return list(group_conditions.keys())

def remove_group_condition(group_name):
    """
    Removes a group condition variable. Use with caution.
    Should only be called when you're sure no threads are waiting on it.
    """
    with group_conditions_lock:
        if group_name in group_conditions:
            del group_conditions[group_name]
            return True
        return False

# --- Helper functions for thread-safe access to global state ---

def get_is_alive():
    """Thread-safe getter for _is_alive."""
    with state_lock:
        return _is_alive

def set_is_alive(val):
    """Thread-safe setter for _is_alive."""
    global _is_alive
    with state_lock:
        old_is_alive = _is_alive
        _is_alive = val
        if old_is_alive != _is_alive:
            print(f"State Change: _is_alive changed from {old_is_alive} to {_is_alive}. Notifying clients.")
            notify_clients_of_state_change()

def get_is_active():
    """Thread-safe getter for _is_active."""
    with state_lock:
        return _is_active

def set_is_active(val):
    """Thread-safe setter for _is_active."""
    global _is_active
    with state_lock:
        old_is_active = _is_active
        _is_active = val
        if old_is_active != _is_active:
            print(f"State Change: _is_active changed from {old_is_active} to {_is_active}. Notifying clients.")
            notify_clients_of_state_change()

def notify_clients_of_state_change(group_name=None):
    """
    Notifies all threads waiting on condition variables that a state has changed.
    If group_name is specified, only notifies that specific group.
    If group_name is None, notifies all groups.
    """
    with group_conditions_lock:
        if group_name:
            # Notify only the specific group
            if group_name in group_conditions:
                with group_conditions[group_name]:
                    group_conditions[group_name].notify_all()
        else:
            # Notify all groups
            for condition in group_conditions.values():
                with condition:
                    condition.notify_all()

# --- SyncManager Class (runs in a separate thread) ---
class SyncManager(threading.Thread):
    """
    Manages synchronization of the 'isActive' status with a peer system.
    Runs in its own thread to periodically check the peer's health.
    """
    def __init__(self, get_alive_func, set_active_func, get_active_func, peer_url):
        super().__init__(name="SyncManagerThread") # Assign a name for easier debugging
        self.get_alive = get_alive_func
        self.set_active = set_active_func
        self.get_active = get_active_func
        self.peer_url = peer_url
        self._stop_event = threading.Event()
        self.daemon = True

    def run(self):
        if not self.peer_url:
            print("SyncManager: PEER_URL not set. Skipping peer synchronization.")
            return

        print(f"SyncManager started, syncing with peer: {self.peer_url}/health")
        while not self._stop_event.is_set():
            try:
                if self.get_alive():
                    response = requests.get(f"{self.peer_url}/health", timeout=5)
                    response.raise_for_status()
                    peer_status = response.json()
                    
                    if peer_status.get('active') is True:
                        if not self.get_active():
                            self.set_active(True) # This will trigger notify_clients_of_state_change()
                            print("SyncManager: Peer is active, setting self to active.")
                    else:
                        if self.get_active():
                            self.set_active(False) # This will trigger notify_clients_of_state_change()
                            print("SyncManager: Peer is inactive, setting self to inactive.")
                else:
                    if self.get_active():
                        self.set_active(False) # This will trigger notify_clients_of_state_change()
                        print("SyncManager: System is not alive, forcing self to inactive.")

            except requests.exceptions.RequestException as e:
                if self.get_active():
                    self.set_active(False) # This will trigger notify_clients_of_state_change()
                    print(f"SyncManager: Error communicating with peer ({self.peer_url}/health): {e}. Setting self to inactive.")
            except Exception as e:
                print(f"SyncManager: An unexpected error occurred: {e}")
            
            self._stop_event.wait(5)

    def stop(self):
        self._stop_event.set()

# --- HTTP Protocol Parsing and Formatting ---

HTTP_STATUS_CODES = {
    200: "OK",
    400: "Bad Request",
    404: "Not Found",
    500: "Internal Server Error",
    503: "Service Unavailable",
    204: "No Content" # For long-polling timeout with no data
}

def parse_http_request(raw_request_data):
    """
    Manually parses a raw HTTP request.
    Returns a dictionary with 'method', 'path', 'headers', and 'body'.
    """
    request_lines = raw_request_data.decode('utf-8').split('\r\n')
    
    # Parse request line (e.g., GET /health HTTP/1.1)
    request_line_parts = request_lines[0].split(' ')
    if len(request_line_parts) < 3:
        raise ValueError("Invalid HTTP request line")
    
    method = request_line_parts[0]
    path = request_line_parts[1]
    
    headers = {}
    body_start_index = -1
    for i, line in enumerate(request_lines[1:]):
        if not line: # Empty line signifies end of headers
            body_start_index = i + 2 # +2 because we are in request_lines[1:] and adding 1 for current line
            break
        parts = line.split(':', 1)
        if len(parts) == 2:
            headers[parts[0].strip().lower()] = parts[1].strip()

    body = ""
    if body_start_index != -1 and body_start_index < len(request_lines):
        body = "\r\n".join(request_lines[body_start_index:])
        # Simple JSON body parsing for POST requests
        if 'content-type' in headers and 'application/json' in headers['content-type'] and body:
            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                body = None # Invalid JSON body

    return {'method': method, 'path': path, 'headers': headers, 'body': body}

def format_http_response(status_code, content_type, body_data):
    """
    Manually formats an HTTP response.
    Returns bytes ready to be sent over the socket.
    """
    try:
        print(f"DEBUG format_http_response: status={status_code}, content_type={content_type}, body_data={body_data}")
        
        status_message = HTTP_STATUS_CODES.get(status_code, "Unknown Status")
        
        # Only serialize body_data if it's not None and status_code is not 204 (No Content)
        body_bytes = b""
        if body_data is not None and status_code != 204:
            if isinstance(body_data, dict):
                body_bytes = json.dumps(body_data).encode('utf-8')
                print(f"DEBUG: Serialized JSON to {len(body_bytes)} bytes: {body_bytes}")
            else:
                body_bytes = str(body_data).encode('utf-8')
                print(f"DEBUG: Converted string to {len(body_bytes)} bytes: {body_bytes}")
        
        print(f"DEBUG: body_bytes length: {len(body_bytes)}")
        
        # Build HTTP response with proper CRLF line endings and CORS headers
        headers = [
            f"HTTP/1.1 {status_code} {status_message}",
            f"Content-Type: {content_type}",
            f"Content-Length: {len(body_bytes)}", 
            "Connection: close",
            # CORS headers
            "Access-Control-Allow-Origin: *",
            "Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS, HEAD",
            "Access-Control-Allow-Headers: Content-Type, Authorization, X-Requested-With",
            "Access-Control-Max-Age: 86400"  # Cache preflight for 24 hours
        ]
        
        # Properly format HTTP response: headers + \r\n\r\n + body
        response_header = "\r\n".join(headers) + "\r\n\r\n"
        result = response_header.encode('utf-8') + body_bytes
        
        print(f"DEBUG: Final response length: {len(result)} bytes")
        print(f"DEBUG: Response headers: {response_header}")
        print(f"DEBUG: Complete response: {result}")
        return result
        
    except Exception as e:
        print(f"ERROR in format_http_response: {e}")
        import traceback
        traceback.print_exc()
        # Return a simple error response
        error_response = b"HTTP/1.1 500 Internal Server Error\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
        return error_response

 
      
# Handler de cliente
def handle_client(client_socket, addr):
    try:
        # Read the HTTP request data
        raw_request_data = b""
        client_socket.settimeout(10)  # Set timeout for reading
        
        # Read the request in chunks
        while True:
            try:
                chunk = client_socket.recv(4096)
                if not chunk:
                    break
                raw_request_data += chunk
                # Check if we have received the complete headers (look for \r\n\r\n)
                if b'\r\n\r\n' in raw_request_data:
                    break
            except socket.timeout:
                print(f"[{threading.current_thread().name}] Socket timeout while reading from {addr}")
                break
            
        if not raw_request_data:
            print(f"[{threading.current_thread().name}] DEBUG: No data from {addr}, closing.")
            return

        print(f"[{threading.current_thread().name}] DEBUG: Received {len(raw_request_data)} bytes from {addr}")

        try:
            print(f"[{threading.current_thread().name}] DEBUG: Parsing HTTP request")
            request_info = parse_http_request(raw_request_data)
            method = request_info['method']
            path = request_info['path']
            print(f"[{threading.current_thread().name}] DEBUG: Parsed request - method={method}, path={path}")
            # body = request_info['body'] # Not used for this logic, but available

            # --- Middleware Logic ---
            # Extract base path without query parameters for middleware check
            base_path = path.split('?')[0]
            allowed_paths = ['/health', '/fall', '/revive', '/groups', '/users', '/login', '/chats', '/messages', '/group-users'] # Base allowed paths
            # Also allow /subscribe/status, /subscribe/user, /notify/, and /user/ with optional query parameters
            subscribe_patterns = ['/subscribe/status', '/subscribe/user', '/notify/', '/user/']
            
            is_allowed_by_middleware = False
            # Check exact matches first
            for allowed_path in allowed_paths:
                if base_path == allowed_path: 
                    is_allowed_by_middleware = True
                    break
            
            # Check subscribe patterns (allowing query parameters)
            if not is_allowed_by_middleware:
                for pattern in subscribe_patterns:
                    if base_path.startswith(pattern):
                        is_allowed_by_middleware = True
                        break

            if (not get_is_alive() or not get_is_active()) and not is_allowed_by_middleware and method != 'OPTIONS':
                print(f"[{threading.current_thread().name}] Request to {path} blocked: System not available (isAlive={get_is_alive()}, isActive={get_is_active()})")
                response_bytes = format_http_response(503, 'application/json', {'error': 'system not available'})
                client_socket.sendall(response_bytes)
                return # End connection after sending error

            # --- Route Handling ---
            response_data = {}
            status_code = 200

            # ...existing code...

            if method == 'POST' and path == '/login':
                # Login: retorna o id do usuário pelo username
                body = request_info.get('body')
                if not body or 'username' not in body:
                    status_code = 400
                    response_data = {'error': 'username é obrigatório'}
                else:
                    with SessionLocal() as session:
                        user = session.query(User).filter(User.username == body['username']).first()
                        if user:
                            # Sync user groups from database
                            sync_user_groups_from_database(user.id)
                            response_data = {'user_id': user.id}
                        else:
                            # Create new user if doesn't exist
                            new_user = User(username=body['username'], password_hash='admin123')
                            session.add(new_user)
                            session.commit() 
                            session.refresh(new_user)  # Get the generated ID
                            # Sync user groups from database (will be empty for new user)
                            sync_user_groups_from_database(new_user.id)
                            response_data = {'user_id': new_user.id, 'created': True}
                response_bytes = format_http_response(status_code, 'application/json', response_data)
                client_socket.sendall(response_bytes)

            elif method == 'GET' and path.startswith('/chats'):
                # Lista os grupos do usuário - using query parameters
                user_id = None
                if '?' in path:
                    query_part = path.split('?', 1)[1]
                    for param in query_part.split('&'):
                        if param.startswith('userId='):
                            user_id = param.split('=', 1)[1]
                            break
                
                if not user_id:
                    status_code = 400
                    response_data = {'error': 'userId query parameter é obrigatório'}
                else:
                    with SessionLocal() as session:
                        user = session.query(User).filter(User.id == user_id).first()
                        if user:
                            chats = [{'id': g.id, 'name': g.name} for g in user.groups]
                            response_data = {'user_id': user.id, 'chats': chats}
                        else:
                            status_code = 404
                            response_data = {'error': 'Usuário não encontrado'}
                response_bytes = format_http_response(status_code, 'application/json', response_data)
                client_socket.sendall(response_bytes)

            elif method == 'GET' and path.startswith('/messages'):
                # Lista mensagens de um grupo - using query parameters
                group_id = None
                if '?' in path:
                    query_part = path.split('?', 1)[1]
                    for param in query_part.split('&'):
                        if param.startswith('groupId='):
                            group_id = param.split('=', 1)[1]
                            break
                
                if not group_id:
                    status_code = 400
                    response_data = {'error': 'groupId query parameter é obrigatório'}
                else:
                    with SessionLocal() as session:
                        group = session.query(Grupo).filter(Grupo.id == group_id).first()
                        if group:
                            messages = [
                                {
                                    'id': m.id,
                                    'sender': m.sender.username,
                                    'content': m.content,
                                    'timestamp': m.timestamp.isoformat()
                                }
                                for m in group.messages
                            ]
                            response_data = {'group_id': group.id, 'messages': messages}
                        else:
                            status_code = 404
                            response_data = {'error': 'Grupo não encontrado'}
                response_bytes = format_http_response(status_code, 'application/json', response_data)
                client_socket.sendall(response_bytes)

            elif method == 'POST' and path == '/messages':
                # Envia mensagem para um grupo
                body = request_info.get('body')
                if not body or not all(k in body for k in ('userId', 'groupId', 'content')):
                    status_code = 400
                    response_data = {'error': 'userId, groupId e content são obrigatórios'}
                else:
                    with SessionLocal() as session:
                        user = session.query(User).filter(User.id == body['userId']).first()
                        group = session.query(Grupo).filter(Grupo.id == body['groupId']).first()
                        if not user or not group:
                            status_code = 404
                            response_data = {'error': 'Usuário ou grupo não encontrado'}
                        else:
                            add_message(session, user, group, body['content'])
                            # Notify group members of new message
                            notify_group_of_change(group.name)
                            response_data = {'message': 'Mensagem enviada'}
                response_bytes = format_http_response(status_code, 'application/json', response_data)
                client_socket.sendall(response_bytes)

            elif method == 'GET' and path.startswith('/group-users'):
                # Lista usuários de um grupo - using query parameters
                group_id = None
                if '?' in path:
                    query_part = path.split('?', 1)[1]
                    for param in query_part.split('&'):
                        if param.startswith('groupId='):
                            group_id = param.split('=', 1)[1]
                            break
                
                if not group_id:
                    status_code = 400
                    response_data = {'error': 'groupId query parameter é obrigatório'}
                else:
                    with SessionLocal() as session:
                        group = session.query(Grupo).filter(Grupo.id == group_id).first()
                        if group:
                            users = [{'id': u.id, 'username': u.username} for u in group.members]
                            response_data = {'group_id': group.id, 'users': users}
                        else:
                            status_code = 404
                            response_data = {'error': 'Grupo não encontrado'}
                response_bytes = format_http_response(status_code, 'application/json', response_data)
                client_socket.sendall(response_bytes)

            elif method == 'DELETE' and path == '/messages':
                # Remove mensagem por id
                body = request_info.get('body')
                if not body or 'messageId' not in body:
                    status_code = 400
                    response_data = {'error': 'messageId é obrigatório'}
                else:
                    with SessionLocal() as session:
                        message = session.query(Message).filter(Message.id == body['messageId']).first()
                        if message:
                            session.delete(message)
                            session.commit()
                            response_data = {'message': 'Mensagem removida'}
                        else:
                            status_code = 404
                            response_data = {'error': 'Mensagem não encontrada'}
                response_bytes = format_http_response(status_code, 'application/json', response_data)
                client_socket.sendall(response_bytes)
            # ...existing code...
            elif method == 'GET':

                    if path == '/':
                        # Send a simple response for the root path
                        response_content = "Render Sanity check!"
                        response_bytes = format_http_response(200, 'text/plain', response_content)
                        client_socket.sendall(response_bytes)
                    elif path == '/health':
                        print(f"[{threading.current_thread().name}] DEBUG: Processing /health request")
                        try:
                            is_alive_val = get_is_alive()
                            is_active_val = get_is_active()
                            print(f"[{threading.current_thread().name}] DEBUG: State - alive={is_alive_val}, active={is_active_val}")
                            response_data = {'status': 'alive' if is_alive_val else 'down', 'active': is_active_val}
                            status_code = 200 if is_alive_val else 503
                            print(f"[{threading.current_thread().name}] DEBUG: Response prepared - status={status_code}, data={response_data}")
                            response_bytes = format_http_response(status_code, 'application/json', response_data)
                            print(f"[{threading.current_thread().name}] DEBUG: Sending response, length={len(response_bytes)}")
                            client_socket.sendall(response_bytes)
                            print(f"[{threading.current_thread().name}] DEBUG: /health response sent successfully")
                        except Exception as e:
                            print(f"[{threading.current_thread().name}] ERROR in /health handler: {e}")
                            import traceback
                            traceback.print_exc()
                    elif path == "/home":
                        html = "<html> <body>Chat</body> </html>"
                        status_code = 200 
                        response_bytes = format_http_response(status_code, 'text/html', html)
                        client_socket.sendall(response_bytes)
                    elif path.startswith('/subscribe/status'):
                        # --- Long-Polling Logic with Group Support ---
                        # Extract group from query parameters or use default
                        group_name = "default"  # Default group
                        if '?' in path:
                            query_part = path.split('?', 1)[1]
                            for param in query_part.split('&'):
                                if param.startswith('group='):
                                    group_name = param.split('=', 1)[1]
                                    break
                        
                        print(f"[{threading.current_thread().name}] Client {addr} started long-polling for status changes in group '{group_name}'.")
                        
                        # Get or create the condition variable for this group
                        group_condition = get_or_create_group_condition(group_name)
                        
                        # Acquire lock before waiting on condition. Wait up to 25 seconds.
                        # The condition variable will release the lock while waiting and re-acquire it upon waking.
                        with group_condition:
                            # Wait for a notification OR for the timeout to expire
                            # This returns True if notified, False if timed out.
                            notified = group_condition.wait(timeout=25) 
                        
                        is_alive_val = get_is_alive() # Get latest state after waiting
                        is_active_val = get_is_active() # Get latest state after waiting
                    
                
            
                        if notified:
                            print(f"[{threading.current_thread().name}] Notified of state change for {addr} in group '{group_name}'. Sending current status.")
                            response_data = {'status': 'alive' if is_alive_val else 'down', 'active': is_active_val, 'change': True, 'group': group_name}
                            status_code = 200
                            response_bytes = format_http_response(status_code, 'application/json', response_data)
                            client_socket.sendall(response_bytes)
                        else:
                            print(f"[{threading.current_thread().name}] Long-poll timeout for {addr} in group '{group_name}'. No state change. Sending 204.")
                            # Send 204 No Content if no change within timeout
                            response_bytes = format_http_response(204, 'application/json', None) 
                            client_socket.sendall(response_bytes)
                    elif path.startswith('/subscribe/user'):
                        # --- User-based Multi-Group Subscription ---
                        # Extract user_id from query parameters
                        user_id = None
                        if '?' in path:
                            query_part = path.split('?', 1)[1]
                            for param in query_part.split('&'):
                                if param.startswith('user_id='):
                                    user_id = param.split('=', 1)[1]
                                    break
                        
                        if not user_id:
                            status_code = 400
                            response_data = {'error': 'user_id parameter is required'}
                            response_bytes = format_http_response(status_code, 'application/json', response_data)
                            client_socket.sendall(response_bytes)
                        else:
                            print(f"[{threading.current_thread().name}] Client {addr} started user-based long-polling for user '{user_id}'.")
                            
                            # Wait for notifications on any of the user's groups
                            notified, notified_group, user_group_list = wait_for_user_group_notifications(user_id, timeout=25)
                            
                            is_alive_val = get_is_alive()
                            is_active_val = get_is_active()

                            if notified:
                                print(f"[{threading.current_thread().name}] User '{user_id}' notified of change in group '{notified_group}'. Sending current status.")
                                response_data = {
                                    'status': 'alive' if is_alive_val else 'down', 
                                    'active': is_active_val, 
                                    'change': True, 
                                    'user_id': user_id,
                                    'notified_group': notified_group,
                                    'user_groups': user_group_list
                                }
                                status_code = 200
                                response_bytes = format_http_response(status_code, 'application/json', response_data)
                                client_socket.sendall(response_bytes)
                            else:
                                print(f"[{threading.current_thread().name}] Long-poll timeout for user '{user_id}'. No state change. Sending 204.")
                                response_bytes = format_http_response(204, 'application/json', None)
                                client_socket.sendall(response_bytes)
                    else: # Unhandled GET paths
                            if get_is_alive() and get_is_active():
                                status_code = 404
                                response_data = {'error': 'Not Found'}
                            else:
                                status_code = 503
                                response_data = {'error': 'system not available'}
                            response_bytes = format_http_response(status_code, 'application/json', response_data)
                            client_socket.sendall(response_bytes)
            elif method == 'POST':
                if path == '/fall':
                    set_is_alive(False) # This will trigger notify_clients_of_state_change()
                    set_is_active(False) # This will trigger notify_clients_of_state_change()
                    print(f"[{threading.current_thread().name}] System status set to DOWN (isAlive=False, isActive=False).")
                    response_data = {'status': 'system down', 'active': get_is_active()}
                elif path == '/revive':
                    set_is_alive(True) # This will trigger notify_clients_of_state_change()
                    print(f"[{threading.current_thread().name}] System status set to REVIVED (isAlive=True).")
                    response_data = {'status': 'system revived', 'active': get_is_active()}
                elif path.startswith('/notify/'):
                    # New endpoint to trigger notifications for specific groups
                    # Example: POST /notify/group1 or POST /notify/all
                    path_parts = path.split('/')
                    if len(path_parts) >= 3:
                        group_target = path_parts[2]
                        if group_target == 'all':
                            notify_clients_of_state_change()  # Notify all groups
                            print(f"[{threading.current_thread().name}] Triggered notification for ALL groups.")
                            response_data = {'message': 'notification sent to all groups'}
                        else:
                            notify_clients_of_state_change(group_target)  # Notify specific group
                            print(f"[{threading.current_thread().name}] Triggered notification for group '{group_target}'.")
                            response_data = {'message': f'notification sent to group {group_target}'}
                    else:
                        status_code = 400
                        response_data = {'error': 'Invalid notify path. Use /notify/{group_name} or /notify/all'}
                
                else: # Unhandled POST paths
                    if get_is_alive() and get_is_active():
                        status_code = 404
                        response_data = {'error': 'Not Found'}
                    else:
                        status_code = 503
                        response_data = {'error': 'system not available'}
                response_bytes = format_http_response(status_code, 'application/json', response_data)
                client_socket.sendall(response_bytes)
            elif method == 'OPTIONS': # <-- CORS Preflight requests
                # Handle CORS preflight requests
                print(f"[{threading.current_thread().name}] DEBUG: Processing OPTIONS request for CORS preflight")
                # Return 200 OK with CORS headers (no body needed)
                response_bytes = format_http_response(200, 'text/plain', None)
                client_socket.sendall(response_bytes)
                print(f"[{threading.current_thread().name}] DEBUG: OPTIONS response sent successfully")
            elif method == 'HEAD': # <-- NOVO BLOCO PARA HEAD
                if path == '/health':
                    print(f"[{threading.current_thread().name}] DEBUG: Processing HEAD /health request (for health check)")
                    is_alive_val = get_is_alive()
                    is_active_val = get_is_active()
                    # A resposta HEAD não tem corpo, mas os cabeçalhos são os mesmos do GET
                    # format_http_response já lida com body_data=None para 204. Para HEAD, podemos enviar
                    # um corpo vazio, mas o importante é que o método HEAD NÃO TEM CORPO.
                    # O status code deve ser o mesmo do GET /health.
                    status_code = 200 if is_alive_val else 503
                    
                    # Para HEAD, o corpo deve ser vazio, mas Content-Length deve ser 0
                    # Modifique format_http_response para lidar com isso explicitamente se necessário.
                    # No seu format_http_response atual, se body_data é None, body_bytes será b"", o que é bom.
                    response_bytes = format_http_response(status_code, 'application/json', None) # Sem corpo para HEAD
                    
                    # Certifique-se de que o Content-Length seja 0 para HEAD
                    # format_http_response já calcula isso com len(body_bytes)
                    client_socket.sendall(response_bytes)
                    print(f"[{threading.current_thread().name}] DEBUG: HEAD /health response sent successfully")
                elif path == '/': # Plataformas podem checar a raiz com HEAD
                    # Se o sistema está ok, responda 200 OK com corpo vazio para HEAD /
                    if get_is_alive() and get_is_active():
                        status_code = 200
                        response_data = None # Sem corpo para HEAD
                    else: # Se o sistema não está ativo, retorne 503 mesmo para HEAD /
                        status_code = 503
                        response_data = {'error': 'system not available'} # Pode ou não ter corpo dependendo da plataforma
                    response_bytes = format_http_response(status_code, 'application/json', response_data)
                    client_socket.sendall(response_bytes)
                else: # Unhandled HEAD paths
                    if get_is_alive() and get_is_active():
                        status_code = 404
                        response_data = {'error': 'Not Found'}
                    else:
                        status_code = 503
                        response_data = {'error': 'system not available'}
                    response_bytes = format_http_response(status_code, 'application/json', response_data)
                    client_socket.sendall(response_bytes) 
            else: # Unhandled methods
                if get_is_alive() and get_is_active():
                    status_code = 404
                    response_data = {'error': 'Not Found'}
                else:
                    status_code = 503
                    response_data = {'error': 'system not available'}
                response_bytes = format_http_response(status_code, 'application/json', response_data)
                client_socket.sendall(response_bytes)

        except ValueError as e:
            print(f"[{threading.current_thread().name}] ERROR: Bad Request from {addr}: {e}")
            response_bytes = format_http_response(400, 'application/json', {'error': 'Bad Request'})
            client_socket.sendall(response_bytes)
        except socket.timeout:
            print(f"[{threading.current_thread().name}] ERROR: Socket timeout for {addr} (initial read).")
        except Exception as e:
            print(f"[{threading.current_thread().name}] ERROR: Exception handling client {addr}: {e}")
            import traceback
            traceback.print_exc()
            try:
                response_bytes = format_http_response(500, 'application/json', {'error': 'Internal Server Error'})
                client_socket.sendall(response_bytes)
            except:
                print(f"[{threading.current_thread().name}] ERROR: Failed to send error response to {addr}")
        # Adiciona um pequeno atraso antes de fechar o socket (pode ajudar com proxies)
        time.sleep(0.1) 
        
    except Exception as e:
        print(f"Error handling client {addr}: {e}")
    finally:
        print(f"[{threading.current_thread().name}] DEBUG: Closing connection with {addr}.")
        try:
            client_socket.close()
        except:
            print(f"[{threading.current_thread().name}] ERROR: Failed to close socket for {addr}")

# --- User-Group Management ---
# Dictionary to store user group memberships
user_groups = {}  # user_id -> set of group_names
user_groups_lock = threading.Lock()

def get_user_groups(user_id):
    """
    Gets the groups that a user belongs to.
    Returns a set of group names.
    """
    with user_groups_lock:
        return user_groups.get(user_id, set()).copy()

def add_user_to_group(user_id, group_name):
    """
    Adds a user to a group.
    """
    with user_groups_lock:
        if user_id not in user_groups:
            user_groups[user_id] = set()
        user_groups[user_id].add(group_name)

def remove_user_from_group(user_id, group_name):
    """
    Removes a user from a group.
    """
    with user_groups_lock:
        if user_id in user_groups:
            user_groups[user_id].discard(group_name)
            if not user_groups[user_id]:  # Remove user if no groups left
                del user_groups[user_id]

def set_user_groups(user_id, group_names):
    """
    Sets all groups for a user (replaces existing groups).
    """
    with user_groups_lock:
        if group_names:
            user_groups[user_id] = set(group_names)
        elif user_id in user_groups:
            del user_groups[user_id]

def get_all_users_in_group(group_name):
    """
    Gets all users that belong to a specific group.
    """
    with user_groups_lock:
        return [user_id for user_id, groups in user_groups.items() if group_name in groups]

def get_all_user_groups():
    """
    Returns a copy of the entire user-group mapping.
    """
    with user_groups_lock:
        return {user_id: groups.copy() for user_id, groups in user_groups.items()}

def wait_for_user_group_notifications(user_id, timeout=25):
    """
    Waits for notifications on any of the groups that a user belongs to.
    Returns (notified, group_that_notified, user_groups).
    """
    user_group_list = list(get_user_groups(user_id))
    
    if not user_group_list:
        # User has no groups, return immediately
        return False, None, []
    
    # Create condition variables for all user groups
    conditions = []
    for group_name in user_group_list:
        conditions.append(get_or_create_group_condition(group_name))
    
    # Use a shared event to coordinate between multiple condition waits
    notification_event = threading.Event()
    notified_group = threading.local()
    notified_group.value = None
    
    def wait_on_condition(condition, group_name):
        """Helper function to wait on a single condition"""
        try:
            with condition:
                if condition.wait(timeout=timeout):
                    notified_group.value = group_name
                    notification_event.set()
        except Exception as e:
            print(f"Error waiting on condition for group {group_name}: {e}")
    
    # Start threads to wait on each condition
    wait_threads = []
    for condition, group_name in zip(conditions, user_group_list):
        thread = threading.Thread(
            target=wait_on_condition, 
            args=(condition, group_name),
            name=f"GroupWaiter-{group_name}"
        )
        thread.daemon = True
        thread.start()
        wait_threads.append(thread)
    
    # Wait for either a notification or timeout
    notified = notification_event.wait(timeout=timeout)
    
    # Clean up - try to join threads quickly
    for thread in wait_threads:
        thread.join(timeout=0.1)
    
    return notified, getattr(notified_group, 'value', None), user_group_list

# --- Enhanced Group Functions ---

def enhanced_notify_clients_of_state_change(group_name=None):
    """
    Enhanced notification function that also considers user-group memberships.
    Notifies all threads waiting on condition variables that a state has changed.
    If group_name is specified, only notifies that specific group.
    If group_name is None, notifies all groups.
    """
    with group_conditions_lock:
        if group_name:
            # Notify only the specific group
            if group_name in group_conditions:
                with group_conditions[group_name]:
                    group_conditions[group_name].notify_all()
            
            # Also notify users in this group
            users_in_group = get_all_users_in_group(group_name)
            for user_id in users_in_group:
                user_groups = get_user_groups(user_id)
                for user_group in user_groups:
                    if user_group != group_name: # Avoid notifying the same group twice
                        with group_conditions[user_group]:
                            group_conditions[user_group].notify_all()
        else:
            # Notify all groups
            for condition in group_conditions.values():
                with condition:
                    condition.notify_all()


# Test function to verify HTTP response format
def test_format_http_response():
    """Test the HTTP response formatting function"""
    test_data = {'status': 'alive', 'active': True}
    response_bytes = format_http_response(200, 'application/json', test_data)
    response_str = response_bytes.decode('utf-8')
    print("="*50)
    print("TEST HTTP RESPONSE:")
    print(repr(response_str))
    print("="*50)
    print("READABLE FORMAT:")
    print(response_str)
    print("="*50)

def sync_user_groups_from_database(user_id):
    """
    Syncs user-group memberships from database to in-memory storage.
    Call this when a user logs in or when group memberships change.
    """
    try:
        with SessionLocal() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                group_names = [group.name for group in user.groups]
                set_user_groups(user_id, group_names)
                print(f"DEBUG: Synced user {user_id} groups: {group_names}")
                return group_names
            else:
                print(f"DEBUG: User {user_id} not found in database")
                return []
    except Exception as e:
        print(f"ERROR syncing user groups for user {user_id}: {e}")
        return []

def notify_group_of_change(group_name):
    """
    Notifies a specific group of changes (like new messages).
    """
    print(f"DEBUG: Notifying group '{group_name}' of changes")
    notify_clients_of_state_change(group_name)



# --- Main Server Loop ---
def start_server_manual_http():
    """
    Starts the HTTP server using raw sockets and a while True loop.
    Each incoming connection is handled in a new thread.
    """
    port = int(os.getenv('PORT', 8080))
    host = '0.0.0.0' # Listen on all interfaces

    print(f"DEBUG: Starting server initialization...")
    print(f"DEBUG: Environment PORT={os.getenv('PORT')}, using port={port}")
    print(f"DEBUG: Binding to host={host}")

    server_socket = None
    try:
        print(f"DEBUG: Creating socket...")
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        print(f"DEBUG: Attempting to bind to {host}:{port}")
        server_socket.bind((host, port))
        
        print(f"DEBUG: Starting to listen...")
        server_socket.listen(5) # Max 5 queued connections
        
        print(f"SUCCESS: HTTP Server listening on http://{host}:{port}/")
        print(f"DEBUG: Server ready to accept connections")

        while True: # Main loop for accepting connections
            print(f"DEBUG: Waiting for connection...")
            conn, addr = server_socket.accept() # Blocks until a new connection
            print(f"DEBUG: Accepted connection from {addr}")
            
            client_thread = threading.Thread(target=handle_client, args=(conn, addr), name=f"ClientHTTPHandler-{addr[0]}:{addr[1]}")
            # The client threads are daemon threads, meaning they will not prevent the main program from exiting
            # if only daemon threads are left. This is suitable for server handlers.
            client_thread.daemon = True 
            client_thread.start()
            print(f"DEBUG: Started thread {client_thread.name} for {addr}")

    except OSError as e:
        if e.errno == 98:
            print(f"Erro: Porta {port} já em uso. Tente novamente mais tarde ou use outra porta.")
        else:
            print(f"Erro de OSError no servidor: {e}")
    except KeyboardInterrupt:
        print("\nServer shutting down due to user interrupt.")
    except Exception as e:
        print(f"Erro inesperado no servidor: {e}")
    finally:
        if server_socket:
            print("Servidor encerrando. Fechando o socket do servidor.")
            server_socket.close()

# --- Main Execution Block ---
if __name__ == '__main__':
    print("="*50)
    print("DEBUG: Application starting...")
    print(f"DEBUG: Python version: {os.sys.version}")
    print(f"DEBUG: Current working directory: {os.getcwd()}")
    print(f"DEBUG: Environment variables:")
    print(f"  PORT: {os.getenv('PORT', 'NOT SET')}")
    print(f"  IS_ACTIVE: {os.getenv('IS_ACTIVE', 'NOT SET')}")
    print(f"  PEER_URL: {os.getenv('PEER_URL', 'NOT SET')}")
    print("="*50)
    
    print(f"Initial State from Environment: IS_ACTIVE={os.getenv('IS_ACTIVE')}, PEER_URL={_peer_url}")
    print(f"Parsed Initial State: isAlive={get_is_alive()}, isActive={get_is_active()}")
    
    # Initialize Sync Manager
    sync_manager = SyncManager(get_is_alive, set_is_active, get_is_active, _peer_url)
    if _peer_url:
        print(f"DEBUG: Starting SyncManager with peer URL: {_peer_url}")
        sync_manager.start()
    else:
        print("DEBUG: No PEER_URL set, skipping SyncManager")

    try:
        print("DEBUG: About to start HTTP server...")
        start_server_manual_http()
    except Exception as e:
        print(f"FATAL ERROR: Exception in main: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if _peer_url:
            print("Stopping SyncManager thread...")
            sync_manager.stop()
            sync_manager.join(timeout=2)
            print("SyncManager thread stopped.")
        print("Application shut down cleanly.")

