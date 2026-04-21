"""
Run storage: Persist and manage debug run logs on disk.

Storage structure:
    backend/logs/runs/
    ├── {run_id}/
    │   ├── metadata.json
    │   ├── steps.json
    │   └── screenshots/
    │       ├── screenshot_1.png
    │       └── screenshot_2.png
"""

import os
import json
import shutil
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# Paths
LOGS_BASE_DIR = Path(__file__).parent.parent.parent / 'logs'
RUNS_DIR = LOGS_BASE_DIR / 'runs'
MAX_RUNS = 50

_storage_lock = threading.Lock()


def ensure_directories():
    """Create necessary directories if they don't exist."""
    RUNS_DIR.mkdir(parents=True, exist_ok=True)


def save_run(
    run_id: str,
    steps: List[Dict[str, Any]],
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Save a run to disk.

    Args:
        run_id: Unique run identifier
        steps: List of step dictionaries
        metadata: Optional run metadata (e.g., target team, status)

    Returns:
        Path to the saved run directory
    """
    ensure_directories()

    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(exist_ok=True)

    # Save metadata
    metadata_path = run_dir / 'metadata.json'
    meta = metadata or {}
    if 'saved_at' not in meta:
        meta['saved_at'] = datetime.utcnow().isoformat() + 'Z'

    with open(metadata_path, 'w') as f:
        json.dump(meta, f, indent=2, default=str)

    # Save steps
    steps_path = run_dir / 'steps.json'
    with open(steps_path, 'w') as f:
        json.dump(steps, f, indent=2, default=str)

    # Prune old runs
    _prune_old_runs()

    return str(run_dir)


def load_run(run_id: str) -> Optional[Dict[str, Any]]:
    """Load a run from disk."""
    run_dir = RUNS_DIR / run_id

    if not run_dir.exists():
        return None

    try:
        steps_path = run_dir / 'steps.json'
        metadata_path = run_dir / 'metadata.json'

        steps = []
        metadata = {}

        if steps_path.exists():
            with open(steps_path, 'r') as f:
                steps = json.load(f)

        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)

        return {
            'run_id': run_id,
            'metadata': metadata,
            'steps': steps,
            'step_count': len(steps),
        }
    except Exception as e:
        print(f"Error loading run {run_id}: {e}")
        return None


def list_runs(limit: int = 50) -> List[Dict[str, Any]]:
    """
    List recent runs with summary info.

    Returns list of runs sorted by creation time (newest first).
    """
    ensure_directories()

    runs = []
    try:
        for run_dir in sorted(RUNS_DIR.iterdir(), reverse=True):
            if not run_dir.is_dir():
                continue

            run_id = run_dir.name
            run_data = load_run(run_id)

            if run_data:
                # Build summary
                steps = run_data.get('steps', [])
                metadata = run_data.get('metadata', {})

                # Extract team target from result or metadata
                team_target = metadata.get('team_target')
                if not team_target and isinstance(metadata.get('result'), dict):
                    team_target = metadata['result'].get('team')
                if not team_target:
                    # Fallback to away_team or home_team
                    team_target = metadata.get('away_team') or metadata.get('home_team')

                summary = {
                    'run_id': run_id,
                    'start_time': steps[0]['timestamp'] if steps else None,
                    'end_time': steps[-1]['timestamp'] if steps else None,
                    'step_count': len(steps),
                    'status': metadata.get('status', 'unknown'),
                    'team_target': team_target,
                    'metadata': metadata,
                }
                runs.append(summary)

                if len(runs) >= limit:
                    break

        return runs
    except Exception as e:
        print(f"Error listing runs: {e}")
        return []


def get_run_summary(run_id: str) -> Optional[Dict[str, Any]]:
    """Get a summary of a specific run (for list view)."""
    run = load_run(run_id)
    if not run:
        return None

    steps = run.get('steps', [])
    metadata = run.get('metadata', {})

    return {
        'run_id': run_id,
        'start_time': steps[0]['timestamp'] if steps else None,
        'end_time': steps[-1]['timestamp'] if steps else None,
        'step_count': len(steps),
        'status': metadata.get('status', 'unknown'),
        'team_target': metadata.get('team_target', None),
    }


def delete_run(run_id: str) -> bool:
    """Delete a run from disk."""
    run_dir = RUNS_DIR / run_id

    try:
        if run_dir.exists():
            shutil.rmtree(run_dir)
            return True
    except Exception as e:
        print(f"Error deleting run {run_id}: {e}")

    return False


def _prune_old_runs():
    """Delete oldest runs if count exceeds MAX_RUNS."""
    with _storage_lock:
        try:
            run_dirs = sorted(
                [d for d in RUNS_DIR.iterdir() if d.is_dir()],
                key=lambda d: d.stat().st_mtime,  # Sort by modification time
            )

            if len(run_dirs) > MAX_RUNS:
                # Delete oldest (first) runs
                to_delete = len(run_dirs) - MAX_RUNS
                for run_dir in run_dirs[:to_delete]:
                    try:
                        shutil.rmtree(run_dir)
                    except Exception as e:
                        print(f"Error deleting old run {run_dir.name}: {e}")
        except Exception as e:
            print(f"Error during run pruning: {e}")


def save_screenshot(
    run_id: str,
    screenshot_data: bytes,
    screenshot_id: str = None,
) -> str:
    """
    Save a screenshot for a run.

    Args:
        run_id: Run ID
        screenshot_data: Image bytes
        screenshot_id: Optional screenshot identifier (defaults to auto-increment)

    Returns:
        Filename of saved screenshot
    """
    ensure_directories()

    run_dir = RUNS_DIR / run_id
    screenshots_dir = run_dir / 'screenshots'
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    # Auto-generate ID if not provided
    if screenshot_id is None:
        existing = len(list(screenshots_dir.glob('*.png')))
        screenshot_id = str(existing + 1)

    filename = f"{screenshot_id}.png"
    filepath = screenshots_dir / filename

    try:
        with open(filepath, 'wb') as f:
            f.write(screenshot_data)
        return filename
    except Exception as e:
        print(f"Error saving screenshot: {e}")
        return None


def get_screenshot(run_id: str, screenshot_id: str) -> Optional[bytes]:
    """Load a screenshot from disk."""
    run_dir = RUNS_DIR / run_id
    filepath = run_dir / 'screenshots' / f"{screenshot_id}.png"

    try:
        if filepath.exists():
            with open(filepath, 'rb') as f:
                return f.read()
    except Exception as e:
        print(f"Error loading screenshot: {e}")

    return None


# Initialize on import
ensure_directories()
