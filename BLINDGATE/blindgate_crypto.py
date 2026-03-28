import hmac
import hashlib
import base64
import socket
import json
from typing import List

# Shared secret key used for DPIEnc-style token encryption
SECRET_KEY = b"blindgate-research-2025"

# Where your IDS listener is running
IDS_HOST = "192.168.182.133"
IDS_PORT = 9000

def normalize_payload(payload: bytes) -> bytes:
	"""
	Normalize payload for case-insensitive, text-oriented matching.
	- Decode as best-effort text
	- Lowercase
	- Re-encode to bytes

	For binary payloads this may lose information, but for HTTP text content
	this is acceptable for the prototype.
	"""
	# errors="ignore" prevents crashes on weird bytes
	text = payload.decode(errors="ignore")
	text_lower = text.lower()
	return text_lower.encode()

def tokenize(payload: bytes, window_size: int = 7) -> List[bytes]:
	"""
	Sliding-window tokenization of the payload.
	Returns list of overlapping byte tokens.
	"""
	tokens = []
	if len(payload) < window_size:
		return tokens
	for i in range(len(payload) - window_size + 1):
		tokens.append(payload[i:i+window_size])
	return tokens

def dpi_enc(tokens: bytes) -> str:
	"""
	Simplified DPIEnc-like function using HMAC-SHA256.
	Returns upper-hex of first 16 bytes for compactness.
	"""
	mac = hmac.new(SECRET_KEY, tokens, hashlib.sha256).digest()
	return base64.b16encode(mac[:16]).decode("ascii")

def send_tokens_to_gateway(flow_id: str, direction: str, payload: bytes):
	"""
	Normalize, tokenize and encrypt payload, then send tokens to Gateway listener as JSON.
	"""
	normalized = normalize_payload(payload)
	tokens = tokenize(normalized)
	enc_tokens = [dpi_enc(t) for t in tokens]

	data = {
		"flow_id": flow_id,
		"direction": direction,
		"token_count": len(enc_tokens),
		"tokens": enc_tokens,
	}

	try:
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.connect((IDS_HOST, IDS_PORT))
		s.sendall((json.dumps(data) + "\n").encode())
		s.close()
		print(f"[BlindGate Crypto] Sent {len(enc_tokens)} tokens to IDS for flow {flow_id}")

	except Exception as e:
		print(f"[BlindGate Crypto] Failed to send tokens to IDS: {e}")
