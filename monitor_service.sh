#!/bin/bash
# Comprehensive monitoring script to diagnose service issues

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOGS_DIR="$SCRIPT_DIR/logs"
MONITOR_LOG="$LOGS_DIR/service_monitor.log"

mkdir -p "$LOGS_DIR"

{
    echo "=== VoiceTV Service Diagnostic Report ==="
    echo "Timestamp: $(date)"
    echo ""
    
    echo "=== Service Status ==="
    if curl -s --connect-timeout 2 http://127.0.0.1:5002/health | jq . 2>/dev/null; then
        echo "Status: RUNNING"
    else
        echo "Status: DOWN"
    fi
    echo ""

    echo "=== Process Information ==="
    ps aux | grep -E "gunicorn.*5002|python.*app.py" | grep -v grep || echo "No processes found"
    echo ""

    echo "=== Network Connections on Port 5002 ==="
    netstat -tlnp 2>/dev/null | grep 5002 || ss -tlnp 2>/dev/null | grep 5002 || echo "Port not listening"
    echo ""

    echo "=== Recent Errors in Logs ==="
    tail -20 "$LOGS_DIR/flask.log" 2>/dev/null | grep -i "error\|exception\|warning" || echo "No recent errors"
    echo ""

    echo "=== Memory Usage ==="
    ps aux | grep -E "gunicorn|python" | grep -v grep | awk '{print "PID " $2 ": " $6 "MB"}'
    echo ""

    echo "=== Disk Space ==="
    df -h "$SCRIPT_DIR" | tail -1
    echo ""

    echo "=== Last 50 lines of Flask Log ==="
    tail -50 "$LOGS_DIR/flask.log" 2>/dev/null || echo "No log file"

} | tee -a "$MONITOR_LOG"

# Keep monitor log to last 1000 lines
tail -1000 "$MONITOR_LOG" > "$MONITOR_LOG.tmp" && mv "$MONITOR_LOG.tmp" "$MONITOR_LOG"
