# main.py (VERSÃO MÍNIMA PARA TESTE DE DEPLOY)
import os
import socket
import threading
import json

# Configuração da porta
# O Render injeta a PORT. Se não estiver lá, isso vai falhar, o que é bom para depurar.
PORT = int(os.environ.get('PORT'))
HOST = '0.0.0.0'

# Função para formatar resposta HTTP
def format_http_response(status_code, content_type, body_data):
    body_bytes = json.dumps(body_data).encode('utf-8') if isinstance(body_data, dict) else str(body_data).encode('utf-8')
    response_lines = [
        f"HTTP/1.1 {status_code} {('OK' if status_code == 200 else 'Not Found' if status_code == 404 else 'Service Unavailable')}",
        f"Content-Type: {content_type}",
        f"Content-Length: {len(body_bytes)}",
        "Connection: close",
        "",
    ]
    return "\r\n".join(response_lines).encode('utf-8') + body_bytes

# Handler de cliente
def handle_client(client_socket, addr):
    try:
        raw_request_data = client_socket.recv(4096)
        if not raw_request_data: return

        request_line = raw_request_data.decode('utf-8').split('\r\n')[0]
        method = request_line.split(' ')[0]
        path = request_line.split(' ')[1]

        print(f"Received {method} {path} from {addr}")

        # Responde 200 OK para /health (GET e HEAD) e para / (HEAD)
        if (method == 'GET' and path == '/health') or \
           (method == 'HEAD' and (path == '/' or path == '/health')):
            response_data = {'status': 'alive', 'active': True}
            response_bytes = format_http_response(200, 'application/json', response_data)
            client_socket.sendall(response_bytes)
        elif method == 'GET' and path == '/home':
            html_content = "<html><body><h1>Hello from Render!</h1></body></html>"
            response_bytes = format_http_response(200, 'text/html', html_content)
            client_socket.sendall(response_bytes)
        else:
            response_bytes = format_http_response(404, 'application/json', {'error': 'Not Found'})
            client_socket.sendall(response_bytes)
    except Exception as e:
        print(f"Error handling client {addr}: {e}")
        client_socket.sendall(format_http_response(500, 'application/json', {'error': 'Internal Server Error'}))
    finally:
        client_socket.close()

# Loop principal do servidor
def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    print(f"Test Server listening on http://{HOST}:{PORT}/")

    while True:
        conn, addr = server_socket.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.daemon = True
        thread.start()

if __name__ == '__main__':
    print(f"Starting application on port {PORT}...")
    try:
        start_server()
    except Exception as e:
        print(f"Fatal error starting server: {e}")
        import traceback
        traceback.print_exc()