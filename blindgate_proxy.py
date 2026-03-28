import socket
import threading
from blindgate_crypto import send_tokens_to_gateway

LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 8080
BUFFER_SIZE = 4096

def recv_until_double_crlf(conn: socket.socket) -> bytes:
	"""
	Read from socket until end of HTTP headers (\r\n\r\n).
	Also returns any extra body data already received.
	"""
	data = b""
	while b"\r\n\r\n" not in data:
		chunk = conn.recv(BUFFER_SIZE)
		if not chunk:
			break
		data += chunk
	return data

def rewrite_request_line(request: bytes) -> bytes:
	"""
	Rewrite proxy-style request line:
	GET http://host/path HTTP/1.1
	into origin-style:
	GET /path HTTP/1.1
	"""
	try:
		headers, rest = request.split(b"\r\n\r\n", 1)
	except ValueError:
		headers = request
		rest = b""

	lines = headers.split(b"\r\n")
	if not lines:
		return request

	request_line = lines[0] # e.g., b"GET http://neverssl.com/ HTTP/1.1"
	parts = request_line.split(b" ")
	if len(parts) < 3:
		return request # malformed, don't touch

	method, uri, version = parts[0], parts[1], parts[2]

	# If URI starts with "http://" or "https://", strip scheme + host
	if uri.startswith(b"http://") or uri.startswith(b"https://"):
		# find first "/" after scheme
		slash_index = uri.find(b"/", uri.find(b"//") + 2)
		if slash_index == -1:
			path = b"/"
		else:
			path = uri[slash_index:]
		new_request_line = b" ".join([method, path, version])
		lines[0] = new_request_line

	new_headers = b"\r\n".join(lines)
	return new_headers + b"\r\n\r\n" + rest

def parse_host_from_headers(request: bytes) -> str:
	"""
	Very naive Host header parser. Good enough for prototype.
	"""
	try:
		headers_part = request.split(b"\r\n\r\n", 1)[0]
		headers_lines = headers_part.split(b"\r\n")
		for line in headers_lines:
			if line.lower().startswith(b"host:"):
				host_value = line.split(b":", 1)[1].strip()
				return host_value.decode()
	except Exception:
		pass
	return ""

def handle_client(client_sock: socket.socket, client_addr):
	try:
		# 1) Receive client HTTP request
		request = recv_until_double_crlf(client_sock)
		if not request:
			client_sock.close()
			return

		# Reject HTTPS tunneling for now
		if request.startswith(b"CONNECT"):
			resp = b"HTTP/1.1 501 Not Implemented\r\nContent-Length: 0\r\n\r\n"
			client_sock.sendall(resp)
			client_sock.close()
			return

		host_header = parse_host_from_headers(request)
		if not host_header:
			print(f"[Proxy] No Host header from {client_addr}, closing.")
			client_sock.close()
			return

		# Extract host + port
		if ":" in host_header:
			host, port_str = host_header.split(":", 1)
			remote_host = host
			remote_port = int(port_str)
		else:
			remote_host = host_header
			remote_port = 80 # default HTTP

		flow_id = f"{client_addr[0]}:{client_addr[1]}->{remote_host}:{remote_port}"
		direction = "outbound"

		print(f"[Proxy] {client_addr} -> {remote_host}:{remote_port}")
		# DEBUG: show first part of the request
		print(f"[DEBUG] First 200 bytes of request:\n{request[:200].decode(errors='ignore')}")

		# Rewrite proxy-style request-line for origin server
		request_upstream = rewrite_request_line(request)
		print(f"[DEBUG] Upstream request line: \n{request_upstream.split(b'\\r\\n', 1)[0].decode(errors='ignore')}")


		# 1a) Send tokens for the REQUEST itself (even if upstream fails)
		try:
			send_tokens_to_gateway(flow_id, direction + "_request", request_upstream)
		except Exception as e:
			print(f"[Proxy] ERROR sending request tokens to gateway: {e}")

		# 2) Connect to remote HTTP server
		try:
			server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			server_sock.connect((remote_host, remote_port))
		except Exception as e:
			print(f"[Proxy] Failed to connect to {remote_host}:{remote_port} - {e}")
			client_sock.close()
			return

		# 3) Forward client request to server
		server_sock.sendall(request_upstream)

		# 4) Read full response from server
		response_chunks = []
		while True:
			chunk = server_sock.recv(BUFFER_SIZE)
			if not chunk:
				break
			response_chunks.append(chunk)

		server_sock.close()

		full_response = b"".join(response_chunks)
		print(f"[Proxy] Got response of {len(full_response)} bytes from {remote_host}:{remote_port}")

		# 5) Send tokens for RESPONSE
		try:
			send_tokens_to_gateway(flow_id, direction + "_response", full_response)
		except Exception as e:
			print(f"[Proxy] ERROR sending response tokens to gateway: {e}")

		# 6) Relay original response back to client
		try:
			client_sock.sendall(full_response)
		except Exception as e:
			print(f"[Proxy] ERROR sending response back to client {client_addr}: {e}")
		finally:
			client_sock.close()

	except Exception as e:
		print(f"[Proxy] Error handling client {client_addr}: {e}")
		try:
			client_sock.close()
		except:
			pass

def start_proxy():
	listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	listen_sock.bind((LISTEN_HOST, LISTEN_PORT))
	listen_sock.listen(100)
	print(f"[Proxy] Listening on {LISTEN_HOST}:{LISTEN_PORT}")

	while True:
		client_sock, client_addr = listen_sock.accept()
		t = threading.Thread(target=handle_client, args=(client_sock, client_addr), daemon=True)
		t.start()

if __name__ == "__main__":
	start_proxy()
