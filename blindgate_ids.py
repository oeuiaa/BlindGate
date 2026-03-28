import socket
import json
import urllib.request

LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 9000

# 1. Load encrypted & tokenized rules

RULES_URL = "http://192.168.182.128:9100/rules"  # <-- Gateway LAN IP
LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 9000

def fetch_encrypted_rules():
    with urllib.request.urlopen(RULES_URL, timeout=5) as resp:
        data = resp.read().decode("utf-8")
        raw = json.loads(data)
        # convert token lists to sets for fast intersection
        return {rule: set(tokens) for rule, tokens in raw.items()}

print(f"[BlindGate IDS] Fetching encrypted rules from {RULES_URL} ...")
ENCRYPTED_RULES = fetch_encrypted_rules()

print("[BlindGate IDS] Loaded encrypted rules:")
for r, toks in ENCRYPTED_RULES.items():
    print(f" Rule '{r}' -> {len(toks)} encrypted tokens")

# 3. Start listener

listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
listener.bind((LISTEN_HOST, LISTEN_PORT))
listener.listen(5)

print(f"[BlindGate] Listening on {LISTEN_HOST}:{LISTEN_PORT} for encrypted tokens...")

while True:
	conn, addr = listener.accept()
	print(f"[BlindGate] Connection from {addr}")

	buffer = b""
	while True:
		chunk = conn.recv(4096)
		if not chunk:
			break
		buffer += chunk

		# Process line-based JSON (as sent by proxy)
		if b"\n" in buffer:
			line, buffer = buffer.split(b"\n", 1)
			try:
				data = json.loads(line.decode())
				flow = data["flow_id"]
				direction = data["direction"]
				tokens = data["tokens"]

				print(f"[BlindGate] Got batch: {flow}, {direction}, tokens={len(tokens)}")

				# RULE MATCHING
				for rule, enc_rule_tokens in ENCRYPTED_RULES.items():
					intersection = enc_rule_tokens.intersection(tokens)
					if intersection:
						print(f"\n [ALERT] Rule MATCHED: '{rule}'")
						print(f"Flow: {flow}")
						print(f"Direction: {direction}")
						print(f"Token hits: {len(intersection)}\n")

			except Exception as e:
				print("[BlindGate] JSON error:", e)

	conn.close()
