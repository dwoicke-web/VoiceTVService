#!/bin/bash
# Monitor and auto-enable ADB Debugging setting on Fire TVs
# Prevents the issue where ADB Debugging gets disabled after power cycles
# Run via cron every 2 hours

IPS=("192.168.4.40" "192.168.4.41" "192.168.4.38" "192.168.4.39")
NAMES=("Upper Left" "Upper Right" "Lower Left" "Lower Right")
LOG_FILE="/var/log/voicetv/adb_debugging_monitor.log"

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_message "=== ADB Debugging Monitor Check ==="

changes_made=0
devices_checked=0
devices_offline=0

for i in "${!IPS[@]}"; do
  ip="${IPS[$i]}"
  name="${NAMES[$i]}"

  devices_checked=$((devices_checked + 1))

  # Check if device is ADB responsive first
  adb -s "$ip:5555" shell getprop ro.serialno &>/dev/null
  if [ $? -ne 0 ]; then
    log_message "⚠ $name ($ip): ADB offline, skipping"
    devices_offline=$((devices_offline + 1))
    continue
  fi

  # Check ADB Debugging status
  status=$(adb -s "$ip:5555" shell settings get secure adb_enabled 2>/dev/null)

  if [ "$status" = "1" ]; then
    log_message "✓ $name ($ip): ADB Debugging already ON"
  elif [ "$status" = "0" ]; then
    log_message "! $name ($ip): ADB Debugging was OFF, re-enabling..."
    adb -s "$ip:5555" shell settings put secure adb_enabled 1 2>/dev/null
    if [ $? -eq 0 ]; then
      log_message "✓ $name ($ip): ADB Debugging re-enabled"
      changes_made=$((changes_made + 1))
    else
      log_message "✗ $name ($ip): Failed to enable ADB Debugging"
    fi
  else
    log_message "? $name ($ip): Could not determine ADB Debugging status (got: '$status')"
  fi
done

# Summary
log_message "=== Summary: $devices_checked checked, $changes_made re-enabled, $devices_offline offline ==="
log_message ""

# Force write to disk to ensure logs persist
sync
