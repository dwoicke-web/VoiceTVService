#!/bin/bash
# Dedicated diagnostic logging for ADB and system state
# Use this for all tests and health checks
# Forces immediate disk writes and timestamps

LOG_FILE="/home/orangepi/Apps/VoiceTVService/logs/diagnostic.log"
mkdir -p "$(dirname "$LOG_FILE")"

log_event() {
  local level="$1"
  local message="$2"
  local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

  # Write to log file immediately (with flush)
  echo "$timestamp - $level - $message" | tee -a "$LOG_FILE"

  # Force disk sync every write
  sync
}

# Usage: log_event INFO "message here"
export -f log_event
export LOG_FILE
