"""Process hygiene for Fire TV launcher subprocesses (mlb_launcher.py / espn_launcher.py / nfl_launcher.py).

Guards against two failure modes seen in production:
  1. Overlapping launches for the same TV — if a new command for a TV fires
     while a previous launcher subprocess for that same IP is still running
     (stuck in a retry loop, or just slow), the two processes independently
     force-stop/tap/navigate the same screen and fight each other. The app
     visibly bounces between loading and the Fire TV home screen. Fix: kill
     any existing launcher for that IP before starting a new one, every time.
  2. Stale processes surviving between sessions — a launcher subprocess
     should never run more than a couple of minutes; one still alive when
     the first command of a new day comes in is presumed orphaned (crashed
     retry loop, killed parent, etc.) and is cleared before anything new
     runs, so the day starts from a known-clean state.
"""
import json
import logging
import os
import subprocess
from datetime import date

logger = logging.getLogger(__name__)

_STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.launch_guard_state.json')

FIRE_TV_IPS = {
    'upper_left': '192.168.4.40',
    'upper_right': '192.168.4.41',
    'lower_left': '192.168.4.38',
    'lower_right': '192.168.4.39',
}


def kill_launcher_for_ip(ip: str):
    """Kill any running mlb_launcher.py/espn_launcher.py/nfl_launcher.py subprocess already targeting this IP."""
    try:
        result = subprocess.run(
            ['pkill', '-f', f'(mlb_launcher|espn_launcher|nfl_launcher)\\.py {ip} '],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            logger.warning(f"launch_guard: killed stale launcher(s) already targeting {ip}")
    except Exception as e:
        logger.warning(f"launch_guard: failed to check/kill launchers for {ip}: {e}")


def kill_all_launchers() -> bool:
    """Kill every running launcher subprocess, across all TVs."""
    try:
        result = subprocess.run(
            ['pkill', '-f', 'mlb_launcher.py|espn_launcher.py|nfl_launcher.py'],
            capture_output=True, text=True
        )
        killed = result.returncode == 0
        if killed:
            logger.warning("launch_guard: killed all running launcher subprocesses")
        return killed
    except Exception as e:
        logger.warning(f"launch_guard: failed to kill all launchers: {e}")
        return False


def ensure_daily_readiness():
    """Run automatically on the first launch command of each day: sweep out
    anything left running from a prior session before taking new commands.
    """
    today = date.today().isoformat()
    last_day = None
    try:
        with open(_STATE_FILE) as f:
            last_day = json.load(f).get('last_command_date')
    except Exception:
        pass

    if last_day == today:
        return

    logger.info(f"launch_guard: first command of {today} — sweeping stale launcher/adb processes")
    kill_all_launchers()

    for name, ip in FIRE_TV_IPS.items():
        try:
            subprocess.run(
                ['bash', '-c', f"kill $(pgrep -f 'adb.*{ip}') 2>/dev/null"],
                capture_output=True, timeout=5
            )
        except Exception:
            pass

    try:
        with open(_STATE_FILE, 'w') as f:
            json.dump({'last_command_date': today}, f)
    except Exception as e:
        logger.warning(f"launch_guard: failed to persist state: {e}")
