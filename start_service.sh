#!/bin/bash
# VoiceTV Service starter with proper environment setup

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$SCRIPT_DIR/backend"
LOGS_DIR="$SCRIPT_DIR/logs"
VENV="$BACKEND_DIR/venv"
PID_FILE="$LOGS_DIR/voicetv.pid"

# Create logs directory if it doesn't exist
mkdir -p "$LOGS_DIR"

# Load environment variables if they exist
if [ -f "$SCRIPT_DIR/.env" ]; then
    export $(cat "$SCRIPT_DIR/.env" | grep -v '^#' | xargs)
fi

# Ensure venv exists
if [ ! -d "$VENV" ]; then
    echo "[$(date)] ERROR: Virtual environment not found at $VENV"
    exit 1
fi

# Kill any existing process on port 5002
echo "[$(date)] Checking for existing process on port 5002..."
if lsof -i :5002 >/dev/null 2>&1; then
    OLD_PID=$(lsof -t -i :5002)
    echo "[$(date)] Killing existing process PID: $OLD_PID"
    kill -9 "$OLD_PID" 2>/dev/null || true
    sleep 2
fi

# Start the Flask app with gunicorn
echo "[$(date)] Starting VoiceTV Service..."
cd "$BACKEND_DIR"

# Export API key if not already set
if [ -z "$ANTHROPIC_API_KEY" ]; then
    export ANTHROPIC_API_KEY="${VOICETV_API_KEY:-}"
fi

$VENV/bin/gunicorn \
    -w 2 \
    -b 0.0.0.0:5002 \
    --timeout 120 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --access-logfile "$LOGS_DIR/gunicorn_access.log" \
    --error-logfile "$LOGS_DIR/gunicorn_error.log" \
    --log-level info \
    app:app &

GUNICORN_PID=$!
echo $GUNICORN_PID > "$PID_FILE"
echo "[$(date)] VoiceTV Service started with PID: $GUNICORN_PID"

# Wait for the process to start and verify port is open
echo "[$(date)] Waiting for service to be ready..."
for i in {1..10}; do
    sleep 1
    if python3 -c "import socket; s = socket.socket(); s.settimeout(1); s.connect_ex(('127.0.0.1', 5002)) == 0" 2>/dev/null; then
        echo "[$(date)] ✓ Service is ready on port 5002"
        exit 0
    fi
    echo "[$(date)] Attempt $i/10 - waiting for port 5002..."
done

echo "[$(date)] ERROR: Service failed to start within 10 seconds"
exit 1
