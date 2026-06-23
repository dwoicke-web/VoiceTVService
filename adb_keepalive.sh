#!/bin/bash
# Keep ADB connections alive by reconnecting periodically
# Called by cron every 30 minutes

IPS=("192.168.4.40" "192.168.4.41" "192.168.4.38" "192.168.4.39")

for ip in "${IPS[@]}"; do
  adb connect "$ip:5555" > /dev/null 2>&1
done

exit 0
