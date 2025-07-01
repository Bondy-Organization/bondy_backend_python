# main.py (VERSÃO ULTRA-SIMPLIFICADA PARA TESTE DE CONECTIVIDADE)
import os
import socket
import threading
import time # Para um pequeno atraso

# Configuração da porta
PORT = int(os.environ.get('PORT'))
HOST = '0.0.0.0'

# Resposta HTTP fixa para qualquer requisição
FIXED_RESPONSE = b"HTTP/1.1 200 OK\r\n" \
                 b"Content-Type: text/plain\r\n" \
                 b"Content-Length: 12\r\n" \
                 b"Connection: close\r\n" \
                 b"\r\n" \
                 b"Hello Render!"

# Handler de cliente
def handle_client(client_socket, addr):
    try:
        # Apenas tenta ler algo para consumir a requisição, não precisa parsear
        client_socket.recv(4096) 
        print(f"Received request from {addr}. Sending fixed response.")
        
        # Envia a resposta fixa
        client_socket.sendall(FIXED_RESPONSE)
        
        # Adiciona um pequeno atraso antes de fechar o socket (pode ajudar com proxies)
        time.sleep(0.1) 
        
    except Exception as e:
        print(f"Error handling client {addr}: {e}")
    finally:
        client_socket.close()
        print(f"Connection with {addr} closed.")

# Loop principal do servidor
def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    print(f"ULTRA-SIMPLE Server listening on http://{HOST}:{PORT}/")

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