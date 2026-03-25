"""
Track what's currently playing on each TV.

Simple JSON file persistence — no database needed.
Stores: service, title, channel (if applicable), and timestamp.
"""

import json
import os
from datetime import datetime

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.now_playing.json')


def _read_state():
    """Read current state from disk."""
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _write_state(state):
    """Write state to disk."""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def set_now_playing(tv_id, service, title, channel=None):
    """Record what's now playing on a TV.

    Args:
        tv_id: TV identifier (upper_left, upper_right, lower_left, lower_right)
        service: Streaming service name (ESPN+, MLB, YouTubeTV, Netflix, etc.)
        title: What's playing (e.g., "Penguins vs Avalanche", "ESPN", "Channel 7")
        channel: Optional channel name for YouTubeTV tunes
    """
    state = _read_state()
    state[tv_id] = {
        'service': service,
        'title': title,
        'channel': channel,
        'started_at': datetime.now().isoformat(),
    }
    _write_state(state)


def clear_now_playing(tv_id):
    """Clear what's playing on a TV (e.g., on power off or reset)."""
    state = _read_state()
    if tv_id in state:
        del state[tv_id]
        _write_state(state)


def clear_all():
    """Clear all TV states."""
    _write_state({})


def get_now_playing():
    """Get what's currently playing on all TVs.

    Returns dict keyed by tv_id with service, title, channel, started_at.
    """
    return _read_state()
