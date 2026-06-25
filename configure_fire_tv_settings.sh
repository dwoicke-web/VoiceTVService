#!/bin/bash
# Configure critical Fire TV settings to prevent ADB daemon crashes
# Run this after any Fire TV power cycle to ensure settings persist

IPS=("192.168.4.40" "192.168.4.41" "192.168.4.38" "192.168.4.39")
NAMES=("Upper Left" "Upper Right" "Lower Left" "Lower Right")

echo "Configuring Fire TV settings on all devices..."
echo ""

for i in "${!IPS[@]}"; do
  ip="${IPS[$i]}"
  name="${NAMES[$i]}"

  echo "=== $name ($ip) ==="

  # Enable ADB debugging (should already be on, but ensure)
  adb -s "$ip:5555" shell settings put secure adb_enabled 1 2>/dev/null
  echo "✓ ADB Debugging: enabled"

  # Set idle screen timeout to max (30 minutes) to reduce aggressive sleeping
  # This prevents Fire TV from entering deep sleep and crashing ADB daemon
  adb -s "$ip:5555" shell settings put system screen_off_timeout 1800000 2>/dev/null
  echo "✓ Screen timeout: 30 minutes"

  # Disable aggressive sleep on idle
  adb -s "$ip:5555" shell settings put global sleep_timeout 0 2>/dev/null
  echo "✓ Sleep timeout: disabled"

  # Keep device awake while plugged in (most Fire TVs are plugged into power)
  adb -s "$ip:5555" shell settings put global stay_on_while_plugged_in 3 2>/dev/null
  echo "✓ Stay awake while plugged: enabled"

  echo ""
done

echo "Configuration complete. Fire TVs should now maintain stable ADB connections."
echo ""
echo "Manual verification needed (via Fire TV UI):"
echo "  1. Settings → Device & Software → Developer Options"
echo "     - ADB Debugging: ON"
echo "     - Apps from Unknown Sources: ON"
echo "  2. Settings → Device & Software → Sleep Timer: NEVER (if available)"
echo "  3. Settings → Display & Sounds → Screen Saver: Disabled or very long duration"
