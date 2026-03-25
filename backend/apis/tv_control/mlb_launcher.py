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


def log(msg):
    print(f"[MLB] {msg}", file=sys.stderr, flush=True)


def _dump_ui(ip):
    """Dump UI and return XML string."""
    _run_adb_command(ip, 'uiautomator dump /sdcard/ui.xml 2>&1', timeout=ADB_TIMEOUT)
    time.sleep(1)
    return _run_adb_command(ip, 'cat /sdcard/ui.xml', timeout=ADB_TIMEOUT)


def _parse_game_grid(xml):
    """Parse game cards from Games tab grid.

    Returns list of rows, each row is a list of game cards (left to right).
    Each card is a list of team names.
    Example: [[['White Sox', 'Athletics'], ['Royals', 'Rangers'], ['Tigers', 'Rockies']],
              [['Angels', 'Dodgers'], ['Guardians', 'D-backs'], ['Rays', 'Phillies']]]
    """
    nodes = re.findall(
        r'text="([^"]+)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
        xml
    )

    # Find y-positions that contain known MLB team names
    team_nodes = []
    for text, x1, y1, x2, y2 in nodes:
        if text.strip().lower() in MLB_TEAMS:
            team_nodes.append((int(x1), int(y1), text.strip()))

    if not team_nodes:
        return []

    # Group y-positions into rows (team names within ~100px are same row)
    all_ys = sorted(set(y for _, y, _ in team_nodes))
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

    rows = []
    for y_group in y_groups:
        y_set = set(y_group)
        # Get all team nodes in this row group
        row_teams = [(x, text) for x, y, text in team_nodes if y in y_set]
        row_teams.sort(key=lambda t: t[0])

        # Group by x-position (cards ~350-600px apart)
        card_xs = sorted(set(x for x, _ in row_teams))
        # Merge x positions that are close (within 50px)
        merged_xs = []
        for x in card_xs:
            if merged_xs and abs(x - merged_xs[-1]) < 50:
                continue
            merged_xs.append(x)

        cards = []
        for cx in merged_xs:
            teams = [name for x, name in row_teams if abs(x - cx) < 50]
            cards.append(teams)
        rows.append(cards)

    return rows


def _navigate_to_games_tab(ip):
    """Navigate to Games tab: UP -> verify -> select. Returns True if game tiles found."""
    _run_adb_command(ip, 'input keyevent KEYCODE_DPAD_UP', timeout=ADB_TIMEOUT)
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
        _run_adb_command(ip, 'input keyevent KEYCODE_DPAD_LEFT', timeout=ADB_TIMEOUT)
        time.sleep(0.3)
    log("Navigated LEFT to Home tab")
    time.sleep(0.5)

    # Now go RIGHT to Games tab — it's typically 1 right of Home
    _run_adb_command(ip, 'input keyevent KEYCODE_DPAD_RIGHT', timeout=ADB_TIMEOUT)
    time.sleep(0.5)

    # Verify we're on Games by checking focused tab text
    xml = _dump_ui(ip)
    focused_tab = _find_focused_tab(xml)
    log(f"Focused tab after RIGHT: '{focused_tab}'")

    if focused_tab and 'game' in focused_tab:
        log("Confirmed on Games tab")
    else:
        # Try one more RIGHT in case layout differs
        _run_adb_command(ip, 'input keyevent KEYCODE_DPAD_RIGHT', timeout=ADB_TIMEOUT)
        time.sleep(0.5)
        xml = _dump_ui(ip)
        focused_tab = _find_focused_tab(xml)
        log(f"Focused tab after 2nd RIGHT: '{focused_tab}'")

    # Select the tab
    _run_adb_command(ip, 'input keyevent KEYCODE_DPAD_CENTER', timeout=ADB_TIMEOUT)
    log("Selected tab, waiting 12s for load")
    time.sleep(12)

    xml = _dump_ui(ip)
    if xml and _parse_game_grid(xml):
        return True
    return False


def _find_focused_card(xml, rows):
    """Find which card in the grid is currently focused. Returns (row, col)."""
    if not xml or not rows:
        return 0, 0

    focused_match = re.search(
        r'focused="true"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml
    )
    if not focused_match:
        focused_match = re.search(
            r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"[^>]*focused="true"', xml
        )
    if not focused_match:
        return 0, 0

    fx, fy = int(focused_match.group(1)), int(focused_match.group(2))

    # Find the team node closest to the focused element
    team_nodes = []
    for text, x1, y1, x2, y2 in re.findall(
        r'text="([^"]+)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml
    ):
        if text.strip().lower() in MLB_TEAMS:
            team_nodes.append((int(x1), int(y1), text.strip()))

    if not team_nodes:
        return 0, 0

    # Find closest team node to focused position
    best_name = None
    min_dist = 99999
    for tx, ty, tname in team_nodes:
        dist = abs(tx - fx) + abs(ty - fy)
        if dist < min_dist:
            min_dist = dist
            best_name = tname

    # Map that team name to a row/col in the grid
    if best_name:
        for ri, row in enumerate(rows):
            for ci, card in enumerate(row):
                if best_name in card:
                    return ri, ci

    return 0, 0


def _select_watch_live(ip, target_team):
    """Find Watch Live button and select it. Returns result dict."""
    btn_xml = _dump_ui(ip)
    watch_live_downs = 0
    if btn_xml:
        btn_nodes = re.findall(
            r'text="([^"]+)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
            btn_xml
        )
        button_texts = []
        for text, x1, y1, x2, y2 in btn_nodes:
            if text.strip().lower() in ('watch live', 'go live', 'resume', 'restart'):
                button_texts.append((text.strip(), int(y1)))
        button_texts.sort(key=lambda t: t[1])
        log(f"Buttons found: {button_texts}")

        wl_pos = next((idx for idx, (t, _) in enumerate(button_texts)
                       if t.lower() in ('watch live', 'go live')), -1)
        if wl_pos > 0:
            watch_live_downs = wl_pos

    for _ in range(watch_live_downs):
        _run_adb_command(ip, 'input keyevent KEYCODE_DPAD_DOWN', timeout=ADB_TIMEOUT)
        time.sleep(0.5)

    _run_adb_command(ip, 'input keyevent KEYCODE_DPAD_CENTER', timeout=ADB_TIMEOUT)
    log("Hit Watch Live")
    return {'success': True, 'team': target_team}


def _retry_games_tab(ip):
    """BACK -> UP -> navigate to Games tab with verification."""
    log("Retrying: BACK -> UP -> find Games tab")
    _run_adb_command(ip, 'input keyevent KEYCODE_BACK', timeout=ADB_TIMEOUT)
    time.sleep(2)
    _run_adb_command(ip, 'input keyevent KEYCODE_DPAD_UP', timeout=ADB_TIMEOUT)
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
        _run_adb_command(ip, 'input keyevent KEYCODE_WAKEUP', timeout=ADB_TIMEOUT)
        log("Sent ADB WAKEUP")
    except Exception as e:
        log(f"ADB WAKEUP failed: {e}")
    time.sleep(2)


def launch_game(ip, away_team, home_team):
    target_team = away_team or home_team

    # Phase 0: Wake the Fire TV
    _wake_tv(ip)

    # Phase 1: Launch app and navigate to Games tab
    log(f"Force-stopping MLB on {ip}")
    _run_adb_command(ip, f'am force-stop {MLB_PKG}', timeout=ADB_TIMEOUT)
    time.sleep(2)

    log(f"Starting MLB app on {ip}")
    _run_adb_command(ip, f'am start -n {MLB_ACTIVITY}', timeout=ADB_TIMEOUT)
    time.sleep(8)

    # Try to get to Games tab, retry up to 3 times
    got_games = _navigate_to_games_tab(ip)
    if not got_games:
        for retry in range(3):
            log(f"No game tiles found, retry {retry + 1}")
            got_games = _retry_games_tab(ip)
            if got_games:
                break

    if not got_games:
        return {'error': 'Could not load Games tab after retries'}

    log("Game tiles loaded successfully")

    # Phase 2: Enter the grid, find target game, navigate to it, verify, select
    _run_adb_command(ip, 'input keyevent KEYCODE_DPAD_DOWN', timeout=ADB_TIMEOUT)
    log("DOWN to enter grid")
    time.sleep(1)

    last_cards_str = None
    stuck_count = 0

    for direction_label, key_dir in [('DOWN', 'KEYCODE_DPAD_DOWN'), ('UP', 'KEYCODE_DPAD_UP')]:
        for scroll in range(10):
            # ── Fresh dump to see current grid state ──
            xml = _dump_ui(ip)
            if not xml or 'text=' not in xml:
                log(f"{direction_label} scroll {scroll}: empty UI dump")
                time.sleep(2)
                continue

            rows = _parse_game_grid(xml)
            all_cards = [card for row in rows for card in row]
            log(f"{direction_label} scroll {scroll}: {all_cards}")

            # If we lost the games grid entirely, recover
            if not rows:
                log("Lost games grid — recovering")
                _run_adb_command(ip, 'input keyevent KEYCODE_BACK', timeout=ADB_TIMEOUT)
                time.sleep(2)
                got_games = _retry_games_tab(ip)
                if got_games:
                    _run_adb_command(ip, 'input keyevent KEYCODE_DPAD_DOWN', timeout=ADB_TIMEOUT)
                    time.sleep(1)
                continue

            # Stuck detection — same cards 3 times means we've hit the edge
            cards_key = str(all_cards)
            if cards_key == last_cards_str:
                stuck_count += 1
                if stuck_count >= 3:
                    log(f"Stuck for {stuck_count} scrolls, switching direction")
                    break
            else:
                stuck_count = 0
                last_cards_str = cards_key

            # ── Find target team in visible cards ──
            target_row, target_col = None, None
            for row_idx, row in enumerate(rows):
                for col_idx, card in enumerate(row):
                    for team_text in card:
                        if target_team.lower() in team_text.lower():
                            target_row, target_col = row_idx, col_idx
                            break
                    if target_row is not None:
                        break
                if target_row is not None:
                    break

            if target_row is None:
                # Target not visible — scroll and try again
                _run_adb_command(ip, f'input keyevent {key_dir}', timeout=ADB_TIMEOUT)
                time.sleep(0.5)
                continue

            log(f"Found {target_team} at row {target_row}, col {target_col}")

            # ── Find which card is currently focused ──
            focused_row, focused_col = _find_focused_card(xml, rows)
            log(f"Focused card at row {focused_row}, col {focused_col}")

            # ── Navigate from focused card to target card ──
            row_diff = target_row - focused_row
            col_diff = target_col - focused_col
            log(f"Navigating: row_diff={row_diff}, col_diff={col_diff}")

            for _ in range(abs(row_diff)):
                key = 'KEYCODE_DPAD_DOWN' if row_diff > 0 else 'KEYCODE_DPAD_UP'
                _run_adb_command(ip, f'input keyevent {key}', timeout=ADB_TIMEOUT)
                time.sleep(0.5)

            for _ in range(abs(col_diff)):
                key = 'KEYCODE_DPAD_RIGHT' if col_diff > 0 else 'KEYCODE_DPAD_LEFT'
                _run_adb_command(ip, f'input keyevent {key}', timeout=ADB_TIMEOUT)
                time.sleep(0.5)

            # ── VERIFY: fresh dump to confirm we're on the right card ──
            time.sleep(0.5)
            verify_xml = _dump_ui(ip)
            if verify_xml:
                verify_rows = _parse_game_grid(verify_xml)
                vf_row, vf_col = _find_focused_card(verify_xml, verify_rows)
                # Check that the focused card contains target team
                if verify_rows and 0 <= vf_row < len(verify_rows) and 0 <= vf_col < len(verify_rows[vf_row]):
                    focused_card_teams = verify_rows[vf_row][vf_col]
                    log(f"Verification: focused card teams = {focused_card_teams}")
                    card_has_target = any(
                        target_team.lower() in t.lower() for t in focused_card_teams
                    )
                    if not card_has_target:
                        log(f"WARNING: focused card {focused_card_teams} does NOT contain {target_team}!")
                        log("Aborting selection — will retry from Games tab")
                        _run_adb_command(ip, 'input keyevent KEYCODE_BACK', timeout=ADB_TIMEOUT)
                        time.sleep(2)
                        got_games = _retry_games_tab(ip)
                        if got_games:
                            _run_adb_command(ip, 'input keyevent KEYCODE_DPAD_DOWN', timeout=ADB_TIMEOUT)
                            time.sleep(1)
                        continue
                else:
                    log(f"Verification: could not determine focused card (vf_row={vf_row}, vf_col={vf_col})")

            # ── SELECT game card ──
            _run_adb_command(ip, 'input keyevent KEYCODE_DPAD_CENTER', timeout=ADB_TIMEOUT)
            log(f"Selected game card for {target_team}")
            time.sleep(2)

            # SELECT broadcast
            _run_adb_command(ip, 'input keyevent KEYCODE_DPAD_CENTER', timeout=ADB_TIMEOUT)
            log("Selected broadcast")
            time.sleep(3)

            # ── Phase 3: Find and select Watch Live ──
            return _select_watch_live(ip, target_team)

        # Reset stuck detection for next direction
        stuck_count = 0
        last_cards_str = None

    return {'error': f'Could not find {target_team} after scanning both directions'}


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
