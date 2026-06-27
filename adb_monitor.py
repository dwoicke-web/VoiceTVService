#!/usr/bin/env python3
"""Monitor ADB connectivity for observability (does not wake devices).

Run periodically via cron to record which Fire TVs are reachable over ADB.
This is purely for visibility/diagnostics: the backend reconnects ADB on
demand before every command (see fire_tv._run_adb_command), so a TV that is
simply asleep needs no recovery here - it will reconnect the moment a command
is sent. We deliberately do NOT send Wake-on-LAN from the monitor, so TVs are
free to sleep normally instead of being woken every few minutes.
"""
import sys
import os
import subprocess
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from apis.tv_control.fire_tv import _is_adb_responsive
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
    """Record which Fire TVs are reachable over ADB (no recovery, no WoL)."""
    import time

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
            # Offline usually just means the TV is asleep/off; the backend will
            # reconnect on demand when a command is sent, so this is informational.
            logger.info(f"… {name} ({ip}): ADB not reachable (likely asleep/off)")
            # Also log to diagnostic file
            subprocess.run(['bash', '-c', f'echo "{timestamp} - OFFLINE - {name} ({ip})" >> /home/orangepi/Apps/VoiceTVService/logs/diagnostic.log'], check=False)

    # Log summary
    status_msg = f"ADB Status: {len(online_devices)}/4 reachable - {', '.join(online_devices) if online_devices else 'NONE'}"
    logger.info(status_msg)
    subprocess.run(['bash', '-c', f'echo "{timestamp} - SUMMARY - {status_msg}" >> /home/orangepi/Apps/VoiceTVService/logs/diagnostic.log && sync'], check=False)

    return len(offline_devices) == 0


if __name__ == '__main__':
    # Observability only: a sleeping/off TV is normal, not a failure, so we
    # exit 0 regardless of reachability. Only a real crash is a non-zero exit.
    try:
        check_all_devices()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Monitor exception: {e}", exc_info=True)
        sys.exit(1)
