#!/usr/bin/env python3
"""Monitor ADB connectivity and attempt recovery if devices go offline.

Run every 5 minutes via cron to detect and recover from ADB daemon crashes.
If recovery fails, logs critical error for manual intervention.
"""
import sys
import os
import subprocess
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from apis.tv_control.fire_tv import (
    _is_adb_responsive, _attempt_adb_recovery, FIRE_TV_MAC_ADDRESSES
)
from logging_config import setup_logging, get_logger

setup_logging()
logger = get_logger('adb_monitor')

FIRE_TVS = {
    '192.168.4.40': 'Upper Left',
    '192.168.4.41': 'Upper Right',
    '192.168.4.38': 'Lower Left',
    '192.168.4.39': 'Lower Right',
}


def check_all_devices():
    """Check all Fire TVs and attempt recovery for offline devices."""
    import time
    import subprocess

    offline_devices = []
    online_devices = []

    # Log check start
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    subprocess.run(['bash', '-c', f'echo "{timestamp} - HEALTH_CHECK_START" >> /home/orangepi/Apps/VoiceTVService/logs/diagnostic.log'], check=False)

    for ip, name in FIRE_TVS.items():
        if _is_adb_responsive(ip):
            online_devices.append(name)
            logger.info(f"✓ {name} ({ip}): ADB responsive")
            # Also log to diagnostic file
            subprocess.run(['bash', '-c', f'echo "{timestamp} - ONLINE - {name} ({ip})" >> /home/orangepi/Apps/VoiceTVService/logs/diagnostic.log'], check=False)
        else:
            offline_devices.append((ip, name))
            logger.warning(f"✗ {name} ({ip}): ADB offline")
            # Also log to diagnostic file
            subprocess.run(['bash', '-c', f'echo "{timestamp} - OFFLINE - {name} ({ip})" >> /home/orangepi/Apps/VoiceTVService/logs/diagnostic.log'], check=False)

    # Log summary
    status_msg = f"ADB Status: {len(online_devices)}/4 online - {', '.join(online_devices) if online_devices else 'NONE'}"
    logger.info(status_msg)
    subprocess.run(['bash', '-c', f'echo "{timestamp} - SUMMARY - {status_msg}" >> /home/orangepi/Apps/VoiceTVService/logs/diagnostic.log && sync'], check=False)

    # Attempt recovery for offline devices
    if offline_devices:
        logger.warning(f"Attempting recovery for {len(offline_devices)} offline device(s)...")
        recovered = []
        failed = []

        for ip, name in offline_devices:
            if _attempt_adb_recovery(ip, name):
                recovered.append(name)
            else:
                failed.append(name)

        if recovered:
            logger.info(f"✓ Recovered: {', '.join(recovered)}")

        if failed:
            logger.critical(
                f"✗ Recovery FAILED for {len(failed)} device(s): {', '.join(failed)}. "
                f"Manual hard reset required."
            )

    return len(offline_devices) == 0


if __name__ == '__main__':
    try:
        all_online = check_all_devices()
        sys.exit(0 if all_online else 1)
    except Exception as e:
        logger.error(f"Monitor exception: {e}", exc_info=True)
        sys.exit(1)
