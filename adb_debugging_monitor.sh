#!/bin/bash
# Monitor ADB health and auto-recover from key corruption or disabled ADB Debugging
# Detects unresponsive devices and clears/reconnects auth keys if needed
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
devices_recovered=0

for i in "${!IPS[@]}"; do
  ip="${IPS[$i]}"
  name="${NAMES[$i]}"

  devices_checked=$((devices_checked + 1))

  # Check if device is ADB responsive
  adb -s "$ip:5555" shell getprop ro.serialno &>/dev/null
  if [ $? -ne 0 ]; then
    # Device is offline - check if ADB Debugging is ON but device is unresponsive
    # (indicates key corruption, not disabled ADB Debugging)
    log_message "⚠ $name ($ip): ADB offline - checking if keys are corrupted..."
    devices_offline=$((devices_offline + 1))
    continue
  fi

  # Device is responsive - check ADB Debugging status
  status=$(adb -s "$ip:5555" shell settings get secure adb_enabled 2>/dev/null)

  if [ "$status" = "1" ]; then
    log_message "✓ $name ($ip): ADB responsive, ADB Debugging ON"
  elif [ "$status" = "0" ]; then
    log_message "! $name ($ip): ADB Debugging OFF, re-enabling..."
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

# If any devices offline, attempt key recovery
if [ $devices_offline -gt 0 ]; then
  log_message "! Detected $devices_offline offline device(s) - attempting key recovery..."
  log_message "! Clearing ADB keys and reconnecting all devices..."

  rm -f ~/.android/adbkey ~/.android/adbkey.pub 2>/dev/null

  # Reconnect to all devices to trigger fresh authorization
  for ip in "${IPS[@]}"; do
    adb connect "$ip:5555" &>/dev/null
  done

  sleep 2

  # Check if recovery worked
  online_count=0
  for ip in "${IPS[@]}"; do
    adb -s "$ip:5555" shell getprop ro.serialno &>/dev/null
    if [ $? -eq 0 ]; then
      online_count=$((online_count + 1))
    fi
  done

  if [ $online_count -eq 4 ]; then
    log_message "✓ Key recovery successful - all 4 devices back online"
    devices_recovered=$((devices_recovered + online_count))
  else
    log_message "⚠ Key recovery partial - $online_count/4 devices online"
  fi
fi

# Summary
log_message "=== Summary: $devices_checked checked, $changes_made re-enabled ADB Debugging, $devices_offline offline (recovered: $devices_recovered) ==="
log_message ""

# Force write to disk to ensure logs persist
sync
