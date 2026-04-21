#!/bin/bash
# Health check and watchdog for VoiceTV Service
# Run this script periodically via cron to monitor and restart the service

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOGS_DIR="$SCRIPT_DIR/logs"
SERVICE_URL="http://127.0.0.1:5002/health"
RESTART_SCRIPT="$SCRIPT_DIR/start_service.sh"
HEALTH_LOG="$LOGS_DIR/health_check.log"
STATE_FILE="$LOGS_DIR/service_state"

# Create logs directory
mkdir -p "$LOGS_DIR"

# Function to log
log_msg() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$HEALTH_LOG"
}

# Function to check service health
check_health() {
    local response
    local http_code

    # Try to reach the health endpoint with timeout
    response=$(curl -s -w "\n%{http_code}" --connect-timeout 3 --max-time 5 "$SERVICE_URL" 2>/dev/null)
    http_code=$(echo "$response" | tail -n1)

    # Check if response indicates service is healthy
    if [ "$http_code" = "200" ]; then
        return 0  # Healthy
    else
        return 1  # Unhealthy
    fi
}

# Function to restart service
restart_service() {
    log_msg "⚠️  Service health check failed. Attempting restart..."

    # Kill any existing process
    if pgrep -f "gunicorn.*5002" > /dev/null; then
        log_msg "Stopping existing process..."
        pkill -f "gunicorn.*5002" || true
        sleep 2
    fi

    # Start the service
    if $RESTART_SCRIPT >> "$HEALTH_LOG" 2>&1; then
        log_msg "✓ Service restarted successfully"

        # Verify restart was successful
        sleep 2
        if check_health; then
            log_msg "✓ Service is responding after restart"
            echo "healthy" > "$STATE_FILE"
            return 0
        else
            log_msg "✗ Service still not responding after restart"
            echo "unhealthy" > "$STATE_FILE"
            return 1
        fi
    else
        log_msg "✗ Failed to restart service"
        echo "restart_failed" > "$STATE_FILE"
        return 1
    fi
}

# Main health check logic
log_msg "Running health check..."

if check_health; then
    log_msg "✓ Service is healthy"
    echo "healthy" > "$STATE_FILE"

    # Keep a rolling history of recent health checks
    HEALTH_HISTORY="$LOGS_DIR/health_history.txt"
    echo "OK" >> "$HEALTH_HISTORY"
    tail -100 "$HEALTH_HISTORY" > "$HEALTH_HISTORY.tmp" && mv "$HEALTH_HISTORY.tmp" "$HEALTH_HISTORY"

else
    log_msg "✗ Service is NOT responding"

    # Increment failure counter
    FAILURE_COUNT_FILE="$LOGS_DIR/failure_count"
    FAILURES=$(cat "$FAILURE_COUNT_FILE" 2>/dev/null || echo 0)
    FAILURES=$((FAILURES + 1))
    echo $FAILURES > "$FAILURE_COUNT_FILE"

    if [ "$FAILURES" -ge 2 ]; then
        log_msg "Service has failed $FAILURES consecutive times. Triggering restart..."
        restart_service
        echo 0 > "$FAILURE_COUNT_FILE"  # Reset counter
    else
        log_msg "First failure detected. Will restart on next check if still down."
    fi
fi

# Cleanup old logs (keep last 30 days)
find "$LOGS_DIR" -name "*.log" -mtime +30 -delete 2>/dev/null || true

exit 0
