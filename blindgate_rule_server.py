#!/usr/bin/env python3
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from encrypted_rule_builder import load_rules_from_file, build_rule

RULES_FILE = "rules.txt"
HOST = "0.0.0.0"
PORT = 9100

def build_encrypted_rules():
    rules = load_rules_from_file(RULES_FILE)
    enc = {r: build_rule(r) for r in rules}
    return enc

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/rules":
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")
            return

        try:
            enc = build_encrypted_rules()
            payload = json.dumps(enc).encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

            print(f"[RuleServer] Served {len(enc)} rules to {self.client_address}")
        except Exception as e:
            msg = f"[RuleServer] ERROR: {e}"
            print(msg)
            self.send_response(500)
            self.end_headers()
            self.wfile.write(msg.encode("utf-8"))

    def log_message(self, format, *args):
        # silence default noisy HTTP logs
        return

if __name__ == "__main__":
    print(f"[RuleServer] Listening on http://{HOST}:{PORT}/rules")
    HTTPServer((HOST, PORT), Handler).serve_forever()
