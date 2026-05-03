#!/bin/bash
# VoiceTV Service starter with proper environment setup (foreground mode for systemd)

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$SCRIPT_DIR/backend"
LOGS_DIR="$SCRIPT_DIR/logs"
VENV="$BACKEND_DIR/venv"

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

# Start the Flask app with gunicorn (in foreground - no & at end)
echo "[$(date)] Starting VoiceTV Service..."
cd "$BACKEND_DIR"

# Export API key if not already set
if [ -z "$ANTHROPIC_API_KEY" ]; then
    export ANTHROPIC_API_KEY="${VOICETV_API_KEY:-}"
fi

# Run gunicorn in foreground (no & at the end so systemd can manage the process)
exec $VENV/bin/gunicorn \
    -w 2 \
    -b 0.0.0.0:5002 \
    --timeout 120 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --access-logfile "$LOGS_DIR/gunicorn_access.log" \
    --error-logfile "$LOGS_DIR/gunicorn_error.log" \
    --log-level info \
    app:app
