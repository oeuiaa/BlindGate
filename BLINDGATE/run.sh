#!/usr/bin/env bash

# ==========================================
# BlindGate HTTP Prototype - One Click Runner
# Persistent, Timestamped Logs
# ==========================================

set -e

PROXY_PORT=8080
IDS_PORT=9000
RULES_PORT=9100
PROXY_LOG_DIR="proxy-logs"
IDS_LOG_DIR="ids-logs"
RULES_LOG_DIR="rules-logs"

# ---- Timestamp ----
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")

PROXY_LOG="${PROXY_LOG_DIR}/${TIMESTAMP}-proxy.log"
IDS_LOG="${IDS_LOG_DIR}/${TIMESTAMP}-ids.log"
RULES_LOG="${RULES_LOG_DIR}/${TIMESTAMP}-ruleserver.log"

echo "=========================================="
echo " BlindGate HTTP Prototype"
echo " Encrypted Token Matching (No Zeek)"
echo "=========================================="

# ---- Create log directory ----
mkdir -p "$PROXY_LOG_DIR"
mkdir -p "$IDS_LOG_DIR"

# ---- Helper: kill process on port ----
kill_port () {
    PORT=$1
    PID=$(lsof -ti tcp:$PORT || true)
    if [ -n "$PID" ]; then
        echo "[*] Killing process on port $PORT (PID $PID)"
        kill -9 $PID
    fi
}

# ---- Cleanup old instances ----
echo "[*] Cleaning up old BlindGate processes..."
kill_port $PROXY_PORT
kill_port $IDS_PORT
kill_port $RULES_PORT
sleep 1

# ---- Check rules file ----
if [ ! -f rules.txt ]; then
    echo "[!] ERROR: rules.txt not found"
    exit 1
fi

# ---- Start HTTP proxy / gateway ----
echo "[*] Starting BlindGate HTTP proxy (trusted gateway)..."
python3 -u blindgate_proxy.py > "$PROXY_LOG" 2>&1 &
PROXY_PID=$!
sleep 1

if ! kill -0 $PROXY_PID 2>/dev/null; then
    echo "[!] ERROR: Proxy failed to start"
    kill $IDS_PID
    exit 1
fi

# ---- Start Rule Server ----
echo "[*] Starting BlindGate Rule Server..."
python3 -u blindgate_rule_server.py > "$RULES_LOG" 2>&1 &
RULES_PID=$!
sleep 1

if ! kill -0 $RULES_PID 2>/dev/null; then
    echo "[!] ERROR: Rule server failed to start"
    kill $RULES_PID
    exit 1
fi

echo "[✓] BlindGate Rule Server running (PID $RULES_PID)"
echo "    Log → $RULES_LOG"


echo "[✓] Proxy running (PID $PROXY_PID)"
echo "    Log → $PROXY_LOG"

echo ""
echo "=========================================="
echo " BlindGate is LIVE"
echo "------------------------------------------"
echo " Client proxy  : 192.168.182.128:8080"
echo " IDS listener  : localhost:9000"
echo " Logs stored in: $LOG_DIR/"
echo "------------------------------------------"
echo " Press Ctrl+C to stop everything"
echo "=========================================="

# ---- Graceful shutdown ----
cleanup () {
    echo ""
    echo "[*] Shutting down BlindGate..."
    kill $PROXY_PID $IDS_PID 2>/dev/null || true
    kill $PROXY_PID $RULES_PID 2>/dev/null || true
    echo "[✓] Logs preserved"
    exit 0
}

trap cleanup SIGINT SIGTERM

# ---- Keep script alive ----
while true; do
    sleep 1
done
