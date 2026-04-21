#!/usr/bin/env python3
"""Standalone MLB game launcher for Fire TV.

Run as a subprocess to avoid ADB connection contention.
Usage: python3 mlb_launcher.py <fire_tv_ip> <away_team> <home_team>

Exits 0 on success, 1 on failure. Prints JSON result to stdout.

Strategy:
  1. Launch MLB app, navigate to Games tab (UP, RIGHT, CENTER)
  2. Games tab shows a 3-column grid of game cards
  3. Scan visible cards for target team, scroll DOWN for more rows
  4. Navigate to target card and select it
  5. Select broadcast, then find and select Watch Live
"""
import sys
import time
import re
import json
import os

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from apis.tv_control.fire_tv import _run_adb_command, _send_wol, FIRE_TV_MAC_ADDRESSES
from debug_logging.step_logger import start_run, log_step, get_current_run_id
from debug_logging import run_storage

MLB_PKG = 'com.bamnetworks.mobile.android.gameday.atbat'
MLB_ACTIVITY = f'{MLB_PKG}/mlb.atbat.activity.MainActivity'
ADB_TIMEOUT = 30.0

MLB_TEAMS = {
    'angels', 'astros', 'athletics', 'blue jays', 'braves', 'brewers',
    'cardinals', 'cubs', 'diamondbacks', 'd-backs', 'dodgers', 'giants',
    'guardians', 'mariners', 'marlins', 'mets', 'nationals', 'orioles',
    'padres', 'phillies', 'pirates', 'rangers', 'rays', 'red sox',
    'reds', 'rockies', 'royals', 'tigers', 'twins', 'white sox', 'yankees',
}

# Map city/abbreviation/alternate names to team name as shown in MLB app
MLB_TEAM_ALIASES = {
    'det': 'tigers', 'detroit': 'tigers',
    'nyy': 'yankees', 'new york yankees': 'yankees', 'ny yankees': 'yankees',
    'nym': 'mets', 'new york mets': 'mets', 'ny mets': 'mets',
    'bos': 'red sox', 'boston': 'red sox',
    'lad': 'dodgers', 'la dodgers': 'dodgers', 'los angeles dodgers': 'dodgers',
    'laa': 'angels', 'la angels': 'angels', 'los angeles angels': 'angels',
    'sf': 'giants', 'san francisco': 'giants',
    'sd': 'padres', 'san diego': 'padres',
    'stl': 'cardinals', 'st. louis': 'cardinals', 'st louis': 'cardinals',
    'tb': 'rays', 'tampa bay': 'rays', 'tampa': 'rays',
    'tor': 'blue jays', 'toronto': 'blue jays',
    'min': 'twins', 'minnesota': 'twins',
    'mil': 'brewers', 'milwaukee': 'brewers',
    'tex': 'rangers', 'texas': 'rangers',
    'kc': 'royals', 'kansas city': 'royals',
    'cle': 'guardians', 'cleveland': 'guardians',
    'chi': 'cubs', 'chc': 'cubs', 'chicago cubs': 'cubs',
    'cws': 'white sox', 'chw': 'white sox', 'chicago white sox': 'white sox',
    'atl': 'braves', 'atlanta': 'braves',
    'hou': 'astros', 'houston': 'astros',
    'sea': 'mariners', 'seattle': 'mariners',
    'oak': 'athletics', 'oakland': 'athletics',
    'pit': 'pirates', 'pittsburgh': 'pirates',
    'phi': 'phillies', 'philadelphia': 'phillies',
    'was': 'nationals', 'wsh': 'nationals', 'washington': 'nationals',
    'ari': 'diamondbacks', 'arizona': 'diamondbacks', 'd-backs': 'diamondbacks',
    'col': 'rockies', 'colorado': 'rockies',
    'mia': 'marlins', 'miami': 'marlins',
    'bal': 'orioles', 'baltimore': 'orioles',
    'cin': 'reds', 'cincinnati': 'reds',
}


def _normalize_team(name):
    """Normalize a team name/abbreviation to the name shown in the MLB app."""
    lower = name.strip().lower()
    # Direct match in team set
    if lower in MLB_TEAMS:
        return lower
    # Alias lookup
    if lower in MLB_TEAM_ALIASES:
        return MLB_TEAM_ALIASES[lower]
    # Partial match — check if any team name contains the input or vice versa
    for team in MLB_TEAMS:
        if lower in team or team in lower:
            return team
    for alias, team in MLB_TEAM_ALIASES.items():
        if lower in alias or alias in lower:
            return team
    return lower  # Return as-is, best effort


def log(msg):
    print(f"[MLB] {msg}", file=sys.stderr, flush=True)


def _adb(ip, cmd):
    """Run ADB command with retry. Fire TV ADB daemon gets sluggish during heavy apps."""
    for attempt in range(5):
        try:
            return _run_adb_command(ip, cmd, timeout=ADB_TIMEOUT)
        except Exception as e:
            if attempt < 4:
                delay = 5 + attempt * 2  # 5, 7, 9, 11 seconds
                log(f"ADB retry {attempt + 1} for '{cmd[:50]}': {e} (wait {delay}s)")
                time.sleep(delay)
            else:
                raise


def _dump_ui(ip):
    """Dump UI and return XML string."""
    _adb(ip, 'uiautomator dump /sdcard/ui.xml 2>&1')
    time.sleep(1)
    return _adb(ip, 'cat /sdcard/ui.xml')


def _get_all_texts(xml):
    """Extract all visible text from UI XML — both text="" and content-desc="".

    MLB app may use either attribute for game info.
    Returns list of (text, x1, y1, x2, y2).
    """
    if not xml:
        return []

    results = []
    seen = set()

    # Get text="" attributes with bounds
    for t, x1, y1, x2, y2 in re.findall(
        r'text="([^"]+)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml
    ):
        key = (t, x1, y1)
        if key not in seen:
            seen.add(key)
            results.append((t, int(x1), int(y1), int(x2), int(y2)))

    # Get content-desc="" attributes with bounds (both attribute orders)
    for desc, x1, y1, x2, y2 in re.findall(
        r'content-desc="([^"]+)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml
    ):
        key = (desc, x1, y1)
        if key not in seen:
            seen.add(key)
            results.append((desc, int(x1), int(y1), int(x2), int(y2)))

    for x1, y1, x2, y2, desc in re.findall(
        r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"[^>]*content-desc="([^"]+)"', xml
    ):
        key = (desc, x1, y1)
        if key not in seen:
            seen.add(key)
            results.append((desc, int(x1), int(y1), int(x2), int(y2)))

    return results


def _parse_game_grid(xml):
    """Parse game cards from Games tab grid.

    Checks BOTH text and content-desc attributes for team names.
    Returns list of rows, each row is a list of game cards (left to right).
    Each card is a dict: {'teams': [...], 'x1': int, 'y1': int, 'x2': int, 'y2': int, 'center_x': int, 'center_y': int}
    Example: [[{'teams': ['White Sox', 'Athletics'], 'center_x': 200, 'center_y': 300, ...}, ...], ...]
    """
    all_texts = _get_all_texts(xml)

    # Find nodes that contain known MLB team names
    team_nodes = []
    for text, x1, y1, x2, y2 in all_texts:
        clean = text.strip().lower()
        if clean in MLB_TEAMS:
            team_nodes.append((x1, y1, x2, y2, text.strip()))
        else:
            # Also check if a content-desc contains a team name as part of a longer string
            for team in MLB_TEAMS:
                if team in clean and len(clean) < 80:  # Avoid giant strings
                    team_nodes.append((x1, y1, x2, y2, text.strip()))
                    break

    if not team_nodes:
        return []

    # Group y-positions into rows (team names within ~100px are same row)
    all_ys = sorted(set(y for _, y, _, _, _ in team_nodes))
    y_groups = []
    for y in all_ys:
        placed = False
        for group in y_groups:
            if abs(y - group[0]) < 100:
                group.append(y)
                placed = True
                break
        if not placed:
            y_groups.append([y])

    # Sort row groups by minimum y
    y_groups.sort(key=lambda g: min(g))

    # Pair up rows: each game card has TWO team names stacked vertically
    # Group consecutive y-groups that are close (within 200px) as one card row
    card_row_groups = []
    for yg in y_groups:
        if card_row_groups and abs(min(yg) - max(card_row_groups[-1][-1])) < 200:
            card_row_groups[-1].append(yg)
        else:
            card_row_groups.append([yg])

    rows = []
    for card_row in card_row_groups:
        y_set = set()
        for yg in card_row:
            y_set.update(yg)

        # Get all team nodes in this card row
        row_teams = [(x1, y1, x2, y2, name) for x1, y1, x2, y2, name in team_nodes if y1 in y_set]
        row_teams.sort(key=lambda t: t[0])

        # Group by x-position into cards (teams within 80px horizontally are same card)
        card_xs = sorted(set(x for x, _, _, _, _ in row_teams))
        merged_xs = []
        for x in card_xs:
            if merged_xs and abs(x - merged_xs[-1]) < 80:
                continue
            merged_xs.append(x)

        cards = []
        for cx in merged_xs:
            card_teams = [(x1, y1, x2, y2, name) for x1, y1, x2, y2, name in row_teams if abs(x1 - cx) < 80]
            if card_teams:
                # Get the bounding box of the whole card area
                min_x = min(t[0] for t in card_teams)
                min_y = min(t[1] for t in card_teams)
                max_x = max(t[2] for t in card_teams)
                max_y = max(t[3] for t in card_teams)
                cards.append({
                    'teams': [t[4] for t in card_teams],
                    'x1': min_x, 'y1': min_y, 'x2': max_x, 'y2': max_y,
                    'center_x': (min_x + max_x) // 2,
                    'center_y': (min_y + max_y) // 2,
                })
        rows.append(cards)

    return rows


def _log_grid(rows, focused_pos=None):
    """Pretty-print the game grid with position labels and highlight focus."""
    log("=" * 60)
    log(f"GAME GRID: {len(rows)} rows")
    for ri, row in enumerate(rows):
        for ci, card in enumerate(row):
            marker = " <<<< FOCUSED" if focused_pos == (ri, ci) else ""
            teams_str = " vs ".join(card['teams'])
            log(f"  [{ri},{ci}] {teams_str}  (x={card['center_x']}, y={card['center_y']}){marker}")
    log("=" * 60)


def _navigate_to_games_tab(ip):
    """Navigate to Games tab: UP -> verify -> select. Returns True if game tiles found."""
    _adb(ip, 'input keyevent KEYCODE_DPAD_UP')
    log("UP to nav bar")
    time.sleep(1)

    return _navigate_to_games_from_nav(ip)


def _find_focused_tab(xml):
    """Find which nav tab is currently focused by checking focused elements near top of screen."""
    if not xml:
        return None
    # Look for focused elements with text near the top nav bar (y < 300)
    matches = re.findall(
        r'text="([^"]*)"[^>]*focused="true"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
        xml
    )
    if not matches:
        # Try reverse attribute order
        matches = re.findall(
            r'focused="true"[^>]*text="([^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
            xml
        )
    for text, x1, y1, x2, y2 in matches:
        if int(y1) < 300 and text.strip():
            return text.strip().lower()
    return None


def _navigate_to_games_from_nav(ip):
    """From the nav bar, navigate LEFT to Home first, then RIGHT to Games, verify, and select."""
    # Go all the way LEFT to ensure we're on Home (leftmost tab)
    for _ in range(5):
        _adb(ip, 'input keyevent KEYCODE_DPAD_LEFT')
        time.sleep(0.3)
    log("Navigated LEFT to Home tab")
    time.sleep(0.5)

    # Now go RIGHT to Games tab — it's typically 1 right of Home
    _adb(ip, 'input keyevent KEYCODE_DPAD_RIGHT')
    time.sleep(0.5)

    # Verify we're on Games by checking focused tab text
    xml = _dump_ui(ip)
    focused_tab = _find_focused_tab(xml)
    log(f"Focused tab after RIGHT: '{focused_tab}'")

    if focused_tab and 'game' in focused_tab:
        log("Confirmed on Games tab")
    else:
        # Try one more RIGHT in case layout differs
        _adb(ip, 'input keyevent KEYCODE_DPAD_RIGHT')
        time.sleep(0.5)
        xml = _dump_ui(ip)
        focused_tab = _find_focused_tab(xml)
        log(f"Focused tab after 2nd RIGHT: '{focused_tab}'")

    # Select the tab
    _adb(ip, 'input keyevent KEYCODE_DPAD_CENTER')
    log("Selected tab, waiting 12s for load")
    time.sleep(12)

    xml = _dump_ui(ip)
    if xml and _parse_game_grid(xml):
        return True
    return False


def _get_focused_bounds(xml):
    """Get bounds of ALL focused elements (there may be nested focused containers)."""
    if not xml:
        return []

    bounds = []
    for pattern in [
        r'focused="true"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
        r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"[^>]*focused="true"',
    ]:
        for m in re.finditer(pattern, xml):
            b = (int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)))
            if b not in bounds:
                bounds.append(b)
    return bounds


def _find_focused_card(xml, rows):
    """Find which card in the grid is currently focused using bounds overlap.

    Returns (row, col) tuple. Uses the same overlap strategy as the ESPN launcher.
    """
    if not xml or not rows:
        return 0, 0

    focused_bounds_list = _get_focused_bounds(xml)
    if not focused_bounds_list:
        log("WARNING: No focused element found in UI dump")
        return 0, 0

    # Find which card has the most overlap with any focused element
    best_pos = (0, 0)
    best_overlap = 0

    for fx1, fy1, fx2, fy2 in focused_bounds_list:
        for ri, row in enumerate(rows):
            for ci, card in enumerate(row):
                # Calculate overlap between focused bounds and card bounds
                ox = max(0, min(fx2, card['x2']) - max(fx1, card['x1']))
                oy = max(0, min(fy2, card['y2']) - max(fy1, card['y1']))
                overlap = ox * oy
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_pos = (ri, ci)

    if best_overlap > 0:
        log(f"Focused card determined by bounds overlap: [{best_pos[0]},{best_pos[1]}] (overlap={best_overlap}px²)")
    else:
        # Fallback: use center-distance of focused element to card centers
        log("No bounds overlap — falling back to distance-based focus detection")
        min_dist = 99999
        for fx1, fy1, fx2, fy2 in focused_bounds_list:
            fcx, fcy = (fx1 + fx2) // 2, (fy1 + fy2) // 2
            for ri, row in enumerate(rows):
                for ci, card in enumerate(row):
                    dist = abs(fcx - card['center_x']) + abs(fcy - card['center_y'])
                    if dist < min_dist:
                        min_dist = dist
                        best_pos = (ri, ci)

    return best_pos


def _select_watch_live(ip, target_team):
    """Find and select WATCH LIVE button specifically. Never select Resume."""

    for attempt in range(3):
        btn_xml = _dump_ui(ip)
        if not btn_xml:
            log(f"Watch button attempt {attempt + 1}: empty UI dump")
            time.sleep(2)
            continue

        all_texts = _get_all_texts(btn_xml)

        # STRICT: Only accept "WATCH LIVE" exactly
        watch_live_button = None
        for text, x1, y1, x2, y2 in all_texts:
            clean = text.strip().lower()
            # ONLY match exact "watch live" — nothing else
            if clean == 'watch live':
                watch_live_button = (text.strip(), y1, (x1+x2)//2)  # (text, y_pos, x_center)
                log(f"✓ FOUND 'WATCH LIVE' at y={y1}")
                break

        if not watch_live_button:
            log(f"Watch button attempt {attempt + 1}: 'WATCH LIVE' not found, trying DOWN")
            _adb(ip, 'input keyevent KEYCODE_DPAD_DOWN')
            time.sleep(1)
            continue

        # Now find the currently focused button to navigate to WATCH LIVE
        focused_texts = [t for t in all_texts if 'focused' in str(t).lower()]

        # Get focused button Y position
        focused_y = None
        for text, x1, y1, x2, y2 in all_texts:
            clean = text.strip().lower()
            # Check if this text is in a focused region
            if clean in ['resume', 'resume from beginning', 'watch from the beginning', 'watch now']:
                focused_y = y1
                log(f"Currently focused: '{text}' at y={y1}")
                break

        watch_live_y = watch_live_button[1]

        # Navigate DOWN to WATCH LIVE if it's below focused button
        if focused_y is not None and watch_live_y > focused_y:
            nav_count = (watch_live_y - focused_y) // 100  # Approximate navigation
            log(f"Navigating DOWN {nav_count} times to reach WATCH LIVE")
            for _ in range(max(1, nav_count)):
                _adb(ip, 'input keyevent KEYCODE_DPAD_DOWN')
                time.sleep(0.5)

        # Press CENTER to select WATCH LIVE
        log(f"Pressing CENTER on 'WATCH LIVE'")
        _adb(ip, 'input keyevent KEYCODE_DPAD_CENTER')
        time.sleep(3)

        # Verify: dump UI again — if watch buttons are GONE, stream started
        verify_xml = _dump_ui(ip)
        if verify_xml:
            verify_texts = _get_all_texts(verify_xml)
            watch_still_visible = any(
                'watch live' in t.lower() or 'resume' in t.lower()
                for t, _, _, _, _ in verify_texts
            )
            if watch_still_visible:
                log(f"Watch buttons still showing after tap — retrying (attempt {attempt + 1})")
                time.sleep(2)
                continue
            else:
                log("Watch buttons gone — stream started!")
                return {'success': True, 'team': target_team}
        else:
            # Can't verify — assume success
            log("Could not verify (empty dump) — assuming stream started")
            return {'success': True, 'team': target_team}

    log("Failed to select WATCH LIVE after 3 attempts")
    return {'success': False, 'team': target_team, 'error': 'Watch Live selection failed'}


def _retry_games_tab(ip):
    """BACK -> UP -> navigate to Games tab with verification."""
    log("Retrying: BACK -> UP -> find Games tab")
    _adb(ip, 'input keyevent KEYCODE_BACK')
    time.sleep(2)
    _adb(ip, 'input keyevent KEYCODE_DPAD_UP')
    time.sleep(1)

    return _navigate_to_games_from_nav(ip)


def _wake_tv(ip):
    """Send Wake-on-LAN and ADB WAKEUP to ensure Fire TV is responsive."""
    mac = FIRE_TV_MAC_ADDRESSES.get(ip)
    if mac:
        log(f"Sending WoL to {ip} ({mac})")
        try:
            _send_wol(mac)
        except Exception as e:
            log(f"WoL failed: {e}")
        time.sleep(3)

    try:
        _adb(ip, 'input keyevent KEYCODE_WAKEUP')
        log("Sent ADB WAKEUP")
    except Exception as e:
        log(f"ADB WAKEUP failed: {e}")
    time.sleep(2)


def _reset_to_mlb_home(ip):
    """Reset to MLB home screen — known good starting point for retry."""
    log("Resetting to MLB home...")
    _adb(ip, f'am force-stop {MLB_PKG}')
    time.sleep(2)
    _adb(ip, f'am start -n {MLB_ACTIVITY}')
    log("Waiting 10s for MLB to reload...")
    time.sleep(10)


def _attempt_launch(ip, target_team):
    """Single attempt to find and launch the target game. Returns result dict or None to retry."""

    # Phase 1: Launch app and navigate to Games tab
    log(f"Force-stopping MLB on {ip}")
    _adb(ip, f'am force-stop {MLB_PKG}')
    time.sleep(2)

    log(f"Starting MLB app on {ip}")
    _adb(ip, f'am start -n {MLB_ACTIVITY}')
    log("Waiting 15s for MLB app to fully load...")
    time.sleep(15)

    # Try to get to Games tab, retry up to 3 times
    got_games = _navigate_to_games_tab(ip)
    if not got_games:
        for retry in range(3):
            log(f"No game tiles found, retry {retry + 1}")
            got_games = _retry_games_tab(ip)
            if got_games:
                break

    if not got_games:
        return None  # Signal outer loop to do full restart

    log("Game tiles loaded successfully")

    # Phase 2: Enter the grid, find target game, navigate to it, verify, select
    _adb(ip, 'input keyevent KEYCODE_DPAD_DOWN')
    log("DOWN to enter grid")
    time.sleep(1)

    # Initial grid scan — examine ALL visible tiles
    xml = _dump_ui(ip)
    rows = _parse_game_grid(xml) if xml else []

    if rows:
        focused_row, focused_col = _find_focused_card(xml, rows)
        _log_grid(rows, focused_pos=(focused_row, focused_col))
    else:
        focused_row, focused_col = 0, 0
        log("WARNING: No game cards found in initial scan")

    last_cards_str = None
    stuck_count = 0

    for direction_label, key_dir in [('DOWN', 'KEYCODE_DPAD_DOWN'), ('UP', 'KEYCODE_DPAD_UP')]:
        for scroll in range(10):
            # ── Fresh dump to see current grid state ──
            if scroll > 0 or not rows:  # Skip first dump if we already have it
                xml = _dump_ui(ip)
                if not xml:
                    log(f"{direction_label} scroll {scroll}: empty UI dump")
                    time.sleep(2)
                    continue
                rows = _parse_game_grid(xml)

            # If we lost the games grid entirely, recover
            if not rows:
                log("Lost games grid — recovering")
                _adb(ip, 'input keyevent KEYCODE_BACK')
                time.sleep(2)
                got_games = _retry_games_tab(ip)
                if got_games:
                    _adb(ip, 'input keyevent KEYCODE_DPAD_DOWN')
                    time.sleep(1)
                continue

            # Get focused position and log full grid
            focused_row, focused_col = _find_focused_card(xml, rows)
            _log_grid(rows, focused_pos=(focused_row, focused_col))

            # Stuck detection — same cards 3 times means we've hit the edge
            all_teams = str([card['teams'] for row in rows for card in row])
            if all_teams == last_cards_str:
                stuck_count += 1
                if stuck_count >= 3:
                    log(f"Stuck for {stuck_count} scrolls, switching direction")
                    break
            else:
                stuck_count = 0
                last_cards_str = all_teams

            # ── Find target team in visible cards ──
            target_row, target_col = None, None
            for row_idx, row in enumerate(rows):
                for col_idx, card in enumerate(row):
                    for team_text in card['teams']:
                        if target_team.lower() in team_text.lower():
                            target_row, target_col = row_idx, col_idx
                            break
                    if target_row is not None:
                        break
                if target_row is not None:
                    break

            if target_row is None:
                # Target not visible — scroll and try again
                log(f"{target_team} NOT found in visible tiles. Scrolling {direction_label}...")
                _adb(ip, f'input keyevent {key_dir}')
                time.sleep(0.5)
                continue

            log(f">>> FOUND {target_team} at [{target_row},{target_col}], "
                f"focus is at [{focused_row},{focused_col}]")

            # ── Navigate to target card with retry ──
            # ADB keypresses can fail silently, so verify and retry up to 3 times
            nav_success = False
            for nav_attempt in range(3):
                if nav_attempt > 0:
                    log(f"--- Navigation retry {nav_attempt} ---")
                    # Re-scan to find current focus position
                    time.sleep(1)
                    retry_xml = _dump_ui(ip)
                    if not retry_xml:
                        continue
                    retry_rows = _parse_game_grid(retry_xml)
                    if not retry_rows:
                        continue
                    focused_row, focused_col = _find_focused_card(retry_xml, retry_rows)
                    _log_grid(retry_rows, focused_pos=(focused_row, focused_col))

                    # Re-find target in the (possibly shifted) grid
                    target_row, target_col = None, None
                    for ri, row in enumerate(retry_rows):
                        for ci, card in enumerate(row):
                            for tt in card['teams']:
                                if target_team.lower() in tt.lower():
                                    target_row, target_col = ri, ci
                                    break
                            if target_row is not None:
                                break
                        if target_row is not None:
                            break
                    if target_row is None:
                        log("Target lost from grid during retry!")
                        break

                row_diff = target_row - focused_row
                col_diff = target_col - focused_col

                if row_diff == 0 and col_diff == 0:
                    log("Already on target card!")
                else:
                    log(f"Navigation plan: {abs(row_diff)} {'DOWN' if row_diff > 0 else 'UP'}, "
                        f"{abs(col_diff)} {'RIGHT' if col_diff > 0 else 'LEFT'}")

                    for i in range(abs(row_diff)):
                        key = 'KEYCODE_DPAD_DOWN' if row_diff > 0 else 'KEYCODE_DPAD_UP'
                        _adb(ip, f'input keyevent {key}')
                        log(f"  Move {'DOWN' if row_diff > 0 else 'UP'} ({i+1}/{abs(row_diff)})")
                        time.sleep(0.8)  # Slightly longer delay for flaky ADB

                    for i in range(abs(col_diff)):
                        key = 'KEYCODE_DPAD_RIGHT' if col_diff > 0 else 'KEYCODE_DPAD_LEFT'
                        _adb(ip, f'input keyevent {key}')
                        log(f"  Move {'RIGHT' if col_diff > 0 else 'LEFT'} ({i+1}/{abs(col_diff)})")
                        time.sleep(0.8)

                # ── VERIFY: fresh dump to confirm we're on the right card ──
                time.sleep(1)
                verify_xml = _dump_ui(ip)
                if not verify_xml:
                    log("VERIFY: empty UI dump — assuming success")
                    nav_success = True
                    break

                verify_rows = _parse_game_grid(verify_xml)
                if not verify_rows:
                    log("VERIFY: no game grid — assuming success")
                    nav_success = True
                    break

                vf_row, vf_col = _find_focused_card(verify_xml, verify_rows)
                _log_grid(verify_rows, focused_pos=(vf_row, vf_col))

                if 0 <= vf_row < len(verify_rows) and 0 <= vf_col < len(verify_rows[vf_row]):
                    focused_card = verify_rows[vf_row][vf_col]
                    log(f"VERIFY: focused card = {focused_card['teams']}")
                    card_has_target = any(
                        target_team.lower() in t.lower() for t in focused_card['teams']
                    )
                    if card_has_target:
                        log(f"VERIFY OK: {target_team} confirmed on focused card!")
                        nav_success = True
                        break
                    else:
                        log(f"VERIFY FAILED: {focused_card['teams']} does NOT contain {target_team}")
                        log("Keypresses may not have registered — will recalculate and retry")
                        # Update focus position for next retry iteration
                        focused_row, focused_col = vf_row, vf_col
                else:
                    log(f"VERIFY: could not determine focused card — assuming success")
                    nav_success = True
                    break

            if not nav_success:
                log("Navigation failed after 3 attempts — restarting from Games tab")
                _adb(ip, 'input keyevent KEYCODE_BACK')
                time.sleep(2)
                got_games = _retry_games_tab(ip)
                if got_games:
                    _adb(ip, 'input keyevent KEYCODE_DPAD_DOWN')
                    time.sleep(1)
                continue

            # ── SELECT game card ──
            _adb(ip, 'input keyevent KEYCODE_DPAD_CENTER')
            log(f"Selected game card for {target_team}")
            time.sleep(2)

            # SELECT broadcast
            _adb(ip, 'input keyevent KEYCODE_DPAD_CENTER')
            log("Selected broadcast")
            time.sleep(3)

            # ── Phase 3: Find and select Watch Live ──
            return _select_watch_live(ip, target_team)

        # Reset stuck detection for next direction
        stuck_count = 0
        last_cards_str = None

    return None  # Signal outer loop to do full restart


def launch_game(ip, away_team, home_team, _run_id=None):
    """Launch a game on MLB Fire TV."""
    # Initialize logging run if not already started
    if _run_id is None:
        _run_id = start_run({
            'type': 'mlb_launcher',
            'ip': ip,
            'away_team': away_team,
            'home_team': home_team,
            'status': 'in_progress',
        })

    raw_target = away_team or home_team
    target_team = _normalize_team(raw_target)
    log(f"Target team: '{raw_target}' -> normalized: '{target_team}'")

    result = None
    try:
        for attempt in range(3):
            if attempt > 0:
                log(f"=== RETRY {attempt} — resetting to MLB home ===")
                _reset_to_mlb_home(ip)
            else:
                # Phase 0: Wake the Fire TV
                _wake_tv(ip)

            try:
                result = _attempt_launch(ip, target_team)
            except Exception as e:
                log(f"Attempt {attempt + 1} failed with exception: {e}")
                result = None

            if result and 'success' in result:
                return result

            log(f"Attempt {attempt + 1} did not succeed, will retry")

        result = {'error': f'Could not find or launch {target_team} after 3 attempts'}
        return result
    finally:
        # Save run metadata with result
        if _run_id:
            # Log the overall execution as a step
            from debug_logging.step_logger import log_step, get_run
            log_step(
                'launch_game',
                {'ip': ip, 'away_team': away_team, 'home_team': home_team},
                result,
                status='success' if (result and 'success' in result) else 'failure',
                duration=0
            )

            # Get the steps from the in-memory run
            run_data = get_run(_run_id)
            steps = run_data.get('steps', []) if run_data else []

            run_metadata = {
                'type': 'mlb_launcher',
                'ip': ip,
                'away_team': away_team,
                'home_team': home_team,
                'status': 'success' if (result and 'success' in result) else 'failure',
                'result': result,
            }
            run_storage.save_run(_run_id, steps, metadata=run_metadata)


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print(json.dumps({'error': 'Usage: mlb_launcher.py <ip> <away_team> <home_team>'}))
        sys.exit(1)

    ip = sys.argv[1]
    away = sys.argv[2]
    home = sys.argv[3]

    try:
        result = launch_game(ip, away, home)
        print(json.dumps(result))
        sys.exit(0 if 'success' in result else 1)
    except Exception as e:
        print(json.dumps({'error': str(e)}))
        sys.exit(1)
