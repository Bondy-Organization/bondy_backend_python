import os
import threading 
import requests
import socket # For raw socket programming
import json   # For handling JSON responses 
from database.database import SessionLocal, User, Grupo, Message, add_message
import time # Para um pequeno atraso
import bcrypt
 
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

        is_me_primary = os.getenv('IS_PRIMARY', 'false').lower() == 'true' 
        
        while not self._stop_event.is_set():
            #time.sleep(5)
            try:
                if self.get_alive():
                    response = requests.get(f"{self.peer_url}/health", timeout=5)
                    response.raise_for_status()
                    peer_status = response.json()
                    
                    peer_is_active = peer_status.get('active') == True
                     
                    if peer_is_active is True:
                        if self.get_active():
                            if not is_me_primary:
                                # If I'm Secondary and peer is active, I should yield to Primary
                                self.set_active(False)
                                print("SyncManager: Peer is active, setting self to inactive (yielding to Primary).")
                    elif peer_is_active is False:
                     
                        if not self.get_active():
                            self.set_active(True)
                            print("SyncManager: Peer is inactive, setting self to active.")
                    
                else:
                    if self.get_active():
                        self.set_active(False)
                        print("SyncManager: This node is not alive, forcing self to inactive.")

            except requests.exceptions.RequestException as e:
                print('SyncManager: Error communicating with peer:', e)
                if not self.get_active():
                    self.set_active(True) 
                #if self.get_active(): 
                    #self.set_active(False) # This will trigger notify_clients_of_state_change()
                    #print(f"SyncManager: Error communicating with peer ({self.peer_url}/health): {e}. Setting self to inactive.")
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
    try:
        # Try UTF-8 first, fallback to latin-1 if that fails
        #try:
        decoded_data = raw_request_data.decode('utf-8')
        #except UnicodeDecodeError:
        #print(f"DEBUG: UTF-8 decode failed, trying latin-1. Raw data length: {len(raw_request_data)}")
        # latin-1 can decode any byte sequence
        #decoded_data = raw_request_data.decode('latin-1')
        
        print(f"DEBUG: Successfully decoded request data: {decoded_data[:200]}...")  # Show first 200 chars
        request_lines = decoded_data.split('\r\n')
        
        # Parse request line (e.g., GET /health HTTP/1.1)
        if not request_lines or not request_lines[0]:
            raise ValueError("Empty request data")
            
        request_line_parts = request_lines[0].split(' ')
        if len(request_line_parts) < 3:
            raise ValueError(f"Invalid HTTP request line: {request_lines[0]}")
        
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
        
    except UnicodeDecodeError as e:
        print(f"DEBUG: Unicode decode error: {e}")
        print(f"DEBUG: Raw data (first 50 bytes): {raw_request_data[:50]}")
        print(f"DEBUG: Raw data as hex: {raw_request_data[:50].hex()}")
        raise ValueError(f"Unable to decode request data: {e}")
    except Exception as e:
        print(f"DEBUG: Error parsing HTTP request: {e}")
        print(f"DEBUG: Raw data length: {len(raw_request_data)}")
        print(f"DEBUG: Raw data (first 50 bytes as hex): {raw_request_data[:50].hex()}")
        raise ValueError(f"Invalid HTTP request format: {e}")

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
            print('checking path ' + base_path + ' for allowed')
            
            # Define paths that are always allowed regardless of system state
            always_allowed_paths = ['/health', '/fall', '/revive']
            
            # Define paths that require the system to be active
            active_required_paths = ['/groups', '/users', '/login', '/chats', '/messages', '/group-users', '/create-chat']
            
            # Define patterns that require the system to be active
            active_required_patterns = ['/subscribe/status', '/subscribe/user', '/notify/', '/user/']
            
            is_allowed_by_middleware = False
            
            # Always allow certain paths regardless of system state
            if base_path in always_allowed_paths:
                is_allowed_by_middleware = True
            # For other paths, check if system is active
            elif get_is_alive() and get_is_active():
                # System is active, allow all other paths
                if base_path in active_required_paths:
                    is_allowed_by_middleware = True
                else:
                    # Check active required patterns
                    for pattern in active_required_patterns:
                        if base_path.startswith(pattern):
                            is_allowed_by_middleware = True
                            break

            if not is_allowed_by_middleware and method != 'OPTIONS': 
                if not get_is_alive():
                    print(f"[{threading.current_thread().name}] Request to {path} blocked: System not alive")
                    response_bytes = format_http_response(503, 'application/json', {'error': 'system not available - not alive'})
                elif not get_is_active():
                    print(f"[{threading.current_thread().name}] Request to {path} blocked: System not active")
                    response_bytes = format_http_response(503, 'application/json', {'error': 'system not available - not active'})
                else:
                    print(f"[{threading.current_thread().name}] Request to {path} blocked: Path not allowed")
                    response_bytes = format_http_response(404, 'application/json', {'error': 'Not Found'})
                client_socket.sendall(response_bytes)
                return # End connection after sending error

            # --- Route Handling ---
            response_data = {}
            status_code = 200

            if method == 'POST' and path == '/login':
                # Login: retorna o id do usuário pelo username
                body = request_info.get('body')
                if not body or 'username' not in body or 'password' not in body:
                    status_code = 400
                    response_data = {'error': 'username é obrigatório'}
                else:
                    with SessionLocal() as session:
                        user = session.query(User).filter(User.username == body['username']).first()
                        if user and bcrypt.checkpw(body['password'].encode('utf-8'), user.password_hash.encode('utf-8')):
                            response_data = {'user_id': user.id}
                            #response_data = {'user_id': user.id, mantive isso porque não entendi o porquê da vírgula
                            #                 }
                        else: # Errados
                            status_code = 401 # Unauthorized
                            response_data = {'error': 'Invalid username or password'}
                            # Create new user if doesn't exist mantive caso dê zebra
                            #new_user = User(username=body['username'],
                            #password_hash='admin123'
                            #)
                            ##session.add(new_user)
                            #session.commit() 
                            #session.refresh(new_user)  # Get the generated ID
                            #response_data = {'user_id': new_user.id, 'created': True}
                response_bytes = format_http_response(status_code, 'application/json', response_data)
                client_socket.sendall(response_bytes)

            elif method == 'POST' and path == '/register':
                body = request_info.get('body')
                if not body or 'username' not in body or 'password' not in body:
                    status_code = 400
                    response_data = {'error': 'username and password are required'}
                else:
                    with SessionLocal() as session:
                        # Check if user already exists
                        existing_user = session.query(User).filter(User.username == body['username']).first()
                        if existing_user:
                            status_code = 409 # Conflict
                            response_data = {'error': 'Username already exists'}
                        else:
                            # Hash the password
                            password_bytes = body['password'].encode('utf-8')
                            salt = bcrypt.gensalt()
                            hashed_password = bcrypt.hashpw(password_bytes, salt)
                            
                            new_user = User(
                                username=body['username'],
                                password_hash=hashed_password.decode('utf-8') # Store as a string
                            )
                            session.add(new_user)
                            session.commit()
                            session.refresh(new_user)
                            
                            status_code = 201 # Created
                            response_data = {'user_id': new_user.id, 'message': 'User created successfully'}
                            
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
                            chats = [
                                {
                                    'id': g.id, 
                                    'name': g.name,
                                    'members': [{'id': m.id, 'username': m.username} for m in g.members]
                                } 
                                for g in user.groups
                            ]
 
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
                print(f"[{threading.current_thread().name}] DEBUG: Received body for /messages: {body}")
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
            
            elif method == 'GET' and path == '/users':
                # Busca usuários por filtro de nome (parcial ou exato)
                 
                filtro_nome = None

                if '?' in path:
                    query_part = path.split('?', 1)[1]
                    for param in query_part.split('&'):
                        if param.startswith('username='):
                            filtro_nome = param.split('=', 1)[1]
                            break
                
                with SessionLocal() as session:
                    query = session.query(User)
                    if filtro_nome:
                        query = query.filter(User.username.ilike(f"%{filtro_nome}%"))
                    users = [{'id': u.id, 'username': u.username} for u in query.all()]
                    response_data = {'users': users}
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

            elif method == 'POST' and path == '/create-chat':
                # Create a new chat group
                body = request_info.get('body')
                if not body or not all(k in body for k in ('groupName', 'creatorId')):
                    status_code = 400
                    response_data = {'error': 'groupName and creatorId are required'}
                else:
                    with SessionLocal() as session:
                        # Check if creator user exists
                        creator = session.query(User).filter(User.id == body['creatorId']).first()
                        if not creator:
                            status_code = 404
                            response_data = {'error': 'Creator user not found'}
                        else:
                            # Check if group name already exists
                            #existing_group = session.query(Grupo).filter(Grupo.name == body['groupName']).first()
                            #if existing_group:
                            #    status_code = 409
                            #    response_data = {'error': 'Group name already exists'}
                            #else:
                                # Create new group
                                new_group = Grupo(name=body['groupName'])
                                session.add(new_group)
                                session.flush()  # To get the ID before commit
                                
                                # Add creator as member
                                new_group.members.append(creator)
                                added_members = [{'id': creator.id, 'username': creator.username}]
                                
                                # Process additional members if provided
                                members_list = body.get('members', [])
                                not_found_members = []
                                
                                if members_list:
                                    for username in members_list:
                                        if username != creator.username:  # Skip creator (already added)
                                            member_user = session.query(User).filter(User.username == username).first()
                                            if member_user:
                                                # Check if member is not already in the group
                                                if member_user not in new_group.members:
                                                    new_group.members.append(member_user)
                                                    added_members.append({'id': member_user.id, 'username': member_user.username})
                                            else:
                                                not_found_members.append(username)
                                
                                session.commit()
                                session.refresh(new_group)
                                
                                # Sync user groups for all members
                                for member in new_group.members:
                                    sync_user_groups_from_database(member.id)
                                
                                response_data = {
                                    'group_id': new_group.id,
                                    'group_name': new_group.name,
                                    'creator_id': creator.id,
                                    'members': added_members
                                }
                                
                                # Include warning about not found members if any
                                if not_found_members:
                                    response_data['warning'] = f'Users not found: {", ".join(not_found_members)}'
                                
                                print(f"DEBUG: Created new group '{new_group.name}' (ID: {new_group.id}) with creator {creator.username} and {len(added_members)-1} additional members")
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
                                
                                # Get recent messages from the notified group
                                recent_messages = []
                                if notified_group:
                                    try:
                                        with SessionLocal() as session:
                                            group = session.query(Grupo).filter(Grupo.name == notified_group).first()
                                            if group:
                                                # Get the last 10 messages from this group
                                                messages = session.query(Message).filter(
                                                    Message.group_id == group.id
                                                ).order_by(Message.timestamp.desc()).limit(10).all()
                                                
                                                recent_messages = [
                                                    {
                                                        'id': m.id,
                                                        'sender': m.sender.username,
                                                        'content': m.content,
                                                        'timestamp': m.timestamp.isoformat(),
                                                        'group_id': m.group_id,
                                                        'group_name': group.name
                                                    }
                                                    for m in reversed(messages)  # Reverse to get chronological order
                                                ]
                                    except Exception as e: 
                                        print(f"ERROR getting recent messages for group {notified_group}: {e}")
                                
                                response_data = { 
                                    'change': True, 
                                    'user_id': user_id,
                                    'notified_group': notified_group,
                                    'user_groups': user_group_list,
                                    'recent_messages': recent_messages,
                                    'messages_count': len(recent_messages)
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
# Database-based user group management (replaces in-memory dictionary)

def get_user_groups(user_id):
    """
    Gets the groups that a user belongs to from the database.
    Returns a set of group names.
    """
    try:
        with SessionLocal() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                group_names = {group.name for group in user.groups}
                return group_names
            else:
                return set()
    except Exception as e:
        print(f"ERROR getting user groups for user {user_id}: {e}")
        return set()

def add_user_to_group(user_id, group_name):
    """
    Adds a user to a group in the database.
    """
    try:
        with SessionLocal() as session:
            user = session.query(User).filter(User.id == user_id).first()
            group = session.query(Grupo).filter(Grupo.name == group_name).first()
            
            if user and group:
                if group not in user.groups:
                    user.groups.append(group)
                    session.commit()
                    print(f"DEBUG: Added user {user_id} to group {group_name}")
                    return True
                else:
                    print(f"DEBUG: User {user_id} already in group {group_name}")
                    return True
            else:
                print(f"DEBUG: User {user_id} or group {group_name} not found")
                return False
    except Exception as e:
        print(f"ERROR adding user {user_id} to group {group_name}: {e}")
        return False

def remove_user_from_group(user_id, group_name):
    """
    Removes a user from a group in the database.
    """
    try:
        with SessionLocal() as session:
            user = session.query(User).filter(User.id == user_id).first()
            group = session.query(Grupo).filter(Grupo.name == group_name).first()
            
            if user and group:
                if group in user.groups:
                    user.groups.remove(group)
                    session.commit()
                    print(f"DEBUG: Removed user {user_id} from group {group_name}")
                    return True
                else:
                    print(f"DEBUG: User {user_id} not in group {group_name}")
                    return True
            else:
                print(f"DEBUG: User {user_id} or group {group_name} not found")
                return False
    except Exception as e:
        print(f"ERROR removing user {user_id} from group {group_name}: {e}")
        return False

def set_user_groups(user_id, group_names):
    """
    Sets all groups for a user (replaces existing groups) in the database.
    """
    try:
        with SessionLocal() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if user:
                # Clear existing groups
                user.groups.clear()
                
                # Add new groups
                for group_name in group_names:
                    group = session.query(Grupo).filter(Grupo.name == group_name).first()
                    if group:
                        user.groups.append(group)
                    else:
                        print(f"DEBUG: Group {group_name} not found when setting user groups")
                
                session.commit()
                print(f"DEBUG: Set user {user_id} groups to: {group_names}")
                return True
            else:
                print(f"DEBUG: User {user_id} not found")
                return False
    except Exception as e:
        print(f"ERROR setting user groups for user {user_id}: {e}")
        return False

def get_all_users_in_group(group_name):
    """
    Gets all users that belong to a specific group from the database.
    Returns a list of user IDs as strings.
    """
    try:
        with SessionLocal() as session:
            group = session.query(Grupo).filter(Grupo.name == group_name).first()
            if group:
                user_ids = [str(member.id) for member in group.members]
                return user_ids
            else:
                return []
    except Exception as e:
        print(f"ERROR getting users in group {group_name}: {e}")
        return []

def get_all_user_groups():
    """
    Returns a dictionary of all user-group mappings from the database.
    """
    try:
        with SessionLocal() as session:
            user_groups_dict = {}
            users = session.query(User).all()
            for user in users:
                group_names = {group.name for group in user.groups}
                if group_names:
                    user_groups_dict[str(user.id)] = group_names
            return user_groups_dict
    except Exception as e:
        print(f"ERROR getting all user groups: {e}")
        return {}

def wait_for_user_group_notifications(user_id, timeout=25):
    """
    Waits for notifications on any of the groups that a user belongs to.
    Returns (notified, group_that_notified, user_groups).
    """
    user_group_list = list(get_user_groups(user_id))
    
    if not user_group_list:
        # User has no groups, return immediately
        print(f"DEBUG: User {user_id} has no groups to wait on.")
        return False, None, []
    
    # Create condition variables for all user groups
    conditions = []
    for group_name in user_group_list:
        print('DEBUG: Waiting on group condition for:', group_name)
        conditions.append(get_or_create_group_condition(group_name))
    
    # Use a shared event to coordinate between multiple condition waits
    notification_event = threading.Event()
    # Use a list to share the notified group name between threads
    notified_group_container = [None]
    
    def wait_on_condition(condition, group_name):
        """Helper function to wait on a single condition"""
        try:
            with condition:
                if condition.wait(timeout=timeout):
                    notified_group_container[0] = group_name
                    print(f"DEBUG: Notified for group {group_name}")
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
    
    # Get the notified group from the container
    notified_group = notified_group_container[0]
    print(f"DEBUG: Final notified_group value: {notified_group}")
    
    return notified, notified_group, user_group_list

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
    Syncs user-group memberships from database.
    This function is now simplified since we query the database directly.
    """
    try:
        group_names = list(get_user_groups(user_id))
        print(f"DEBUG: User {user_id} groups from database: {group_names}")
        return group_names
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
    port = int(os.getenv('PORT', 8082))
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

