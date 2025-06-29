import os
import threading 
import requests
import socket # For raw socket programming
import json   # For handling JSON responses 

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
# This condition variable is used to notify waiting clients when a state change occurs.
# It shares the same lock (_state_lock) to ensure consistent state access.
state_change_condition = threading.Condition(state_lock)

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

def notify_clients_of_state_change():
    """
    Notifies all threads waiting on the state_change_condition that a state has changed.
    This wakes up long-polling clients.
    """
    with state_change_condition: # Acquire lock before notifying
        state_change_condition.notify_all() # Wake up all waiting threads

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
    status_message = HTTP_STATUS_CODES.get(status_code, "Unknown Status")
    
    # Only serialize body_data if it's not None and status_code is not 204 (No Content)
    body_bytes = b""
    if body_data is not None and status_code != 204:
        body_bytes = json.dumps(body_data).encode('utf-8') if isinstance(body_data, dict) else str(body_data).encode('utf-8')
    
    response_lines = [
        f"HTTP/1.1 {status_code} {status_message}",
        f"Content-Type: {content_type}",
        f"Content-Length: {len(body_bytes)}",
        "Connection: close", # Simple connection handling for this example
        "", # Empty line separating headers from body
    ]
    
    response_header = "\r\n".join(response_lines).encode('utf-8')
    
    return response_header + body_bytes

# --- Client Handler (runs in a separate thread for each client) ---
def handle_client(client_socket, addr):
    """
    Handles a single client connection.
    Reads request, applies middleware, routes, and sends response.
    """
    print(f"[{threading.current_thread().name}] Cliente conectado: {addr}")
    try:
        # Read the initial request
        client_socket.settimeout(10) # Short timeout for initial request read
        raw_request_data = client_socket.recv(4096) 
        
        if not raw_request_data:
            print(f"[{threading.current_thread().name}] No data from {addr}, closing.")
            return

        try:
            request_info = parse_http_request(raw_request_data)
            method = request_info['method']
            path = request_info['path']
            # body = request_info['body'] # Not used for this logic, but available

            # --- Middleware Logic ---
            allowed_paths = ['/health', '/fall', '/revive', '/subscribe/status'] # Added long-polling path
            
            is_allowed_by_middleware = False
            for allowed_path in allowed_paths:
                if path == allowed_path: 
                    is_allowed_by_middleware = True
                    break

            if (not get_is_alive() or not get_is_active()) and not is_allowed_by_middleware:
                print(f"[{threading.current_thread().name}] Request to {path} blocked: System not available (isAlive={get_is_alive()}, isActive={get_is_active()})")
                response_bytes = format_http_response(503, 'application/json', {'error': 'system not available'})
                client_socket.sendall(response_bytes)
                return # End connection after sending error

            # --- Route Handling ---
            response_data = {}
            status_code = 200

            if method == 'GET':
                if path == '/health':
                    is_alive_val = get_is_alive()
                    is_active_val = get_is_active()
                    response_data = {'status': 'alive' if is_alive_val else 'down', 'active': is_active_val}
                    status_code = 200 if is_alive_val else 503
                    response_bytes = format_http_response(status_code, 'application/json', response_data)
                    client_socket.sendall(response_bytes)
                elif path == "/home":
                    html = "<html> <body>Chat</body> </html>"
                    status_code = 200 
                    response_bytes = format_http_response(status_code, '?', html)
                    client_socket.sendall(response_bytes)
                elif path == '/subscribe/status':
                    # --- Long-Polling Logic ---
                    # We send an initial response only if there's a state change during the wait.
                    # Otherwise, we signal "no change" after timeout.
                    
                    # Store initial state for comparison (optional, but good for client to know what they saw last)
                    # For simplicity here, we always send the current state if notified or on timeout.
                    
                    print(f"[{threading.current_thread().name}] Client {addr} started long-polling for status changes.")
                    
                    # Acquire lock before waiting on condition. Wait up to 25 seconds.
                    # The condition variable will release the lock while waiting and re-acquire it upon waking.
                    with state_change_condition:
                        # Wait for a notification OR for the timeout to expire
                        # This returns True if notified, False if timed out.
                        notified = state_change_condition.wait(timeout=25) 
                    
                    is_alive_val = get_is_alive() # Get latest state after waiting
                    is_active_val = get_is_active() # Get latest state after waiting

                    if notified:
                        print(f"[{threading.current_thread().name}] Notified of state change for {addr}. Sending current status.")
                        response_data = {'status': 'alive' if is_alive_val else 'down', 'active': is_active_val, 'change': True}
                        status_code = 200
                        response_bytes = format_http_response(status_code, 'application/json', response_data)
                        client_socket.sendall(response_bytes)
                    else:
                        print(f"[{threading.current_thread().name}] Long-poll timeout for {addr}. No state change. Sending 204.")
                        # Send 204 No Content if no change within timeout
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
                else: # Unhandled POST paths
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
            print(f"[{threading.current_thread().name}] Bad Request from {addr}: {e}")
            response_bytes = format_http_response(400, 'application/json', {'error': 'Bad Request'})
            client_socket.sendall(response_bytes)
        except socket.timeout:
            print(f"[{threading.current_thread().name}] Socket timeout for {addr} (initial read).")
        except Exception as e:
            print(f"[{threading.current_thread().name}] Erro ao lidar com cliente {addr}: {e}")
            response_bytes = format_http_response(500, 'application/json', {'error': 'Internal Server Error'})
            client_socket.sendall(response_bytes)
    finally:
        print(f"[{threading.current_thread().name}] Fechando conexão com {addr}.")
        client_socket.close()

# --- Main Server Loop ---
def start_server_manual_http():
    """
    Starts the HTTP server using raw sockets and a while True loop.
    Each incoming connection is handled in a new thread.
    """
    port = int(os.getenv('PORT', 8083))
    host = '0.0.0.0' # Listen on all interfaces

    server_socket = None
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((host, port))
        server_socket.listen(5) # Max 5 queued connections
        print(f"HTTP Server manual escutando em http://{host}:{port}/")

        while True: # Main loop for accepting connections
            conn, addr = server_socket.accept() # Blocks until a new connection
            client_thread = threading.Thread(target=handle_client, args=(conn, addr), name=f"ClientHTTPHandler-{addr[0]}:{addr[1]}")
            # The client threads are daemon threads, meaning they will not prevent the main program from exiting
            # if only daemon threads are left. This is suitable for server handlers.
            client_thread.daemon = True 
            client_thread.start()

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
    print(f"Initial State from Environment: IS_ACTIVE={os.getenv('IS_ACTIVE')}, PEER_URL={_peer_url}")
    print(f"Parsed Initial State: isAlive={get_is_alive()}, isActive={get_is_active()}")
    
    # Initialize Sync Manager
    sync_manager = SyncManager(get_is_alive, set_is_active, get_is_active, _peer_url)
    if _peer_url:
        sync_manager.start()

    try:
        start_server_manual_http()
    finally:
        if _peer_url:
            print("Stopping SyncManager thread...")
            sync_manager.stop()
            sync_manager.join(timeout=2)
            print("SyncManager thread stopped.")
        print("Application shut down cleanly.")

