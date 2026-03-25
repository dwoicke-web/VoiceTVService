#!/usr/bin/env python3
"""Standalone ESPN+ game launcher for Fire TV.

Run as a subprocess to avoid ADB connection contention.
Usage: python3 espn_launcher.py <fire_tv_ip> <away_team> <home_team>

Exits 0 on success, 1 on failure. Prints JSON result to stdout.

Strategy:
  1. Wake Fire TV, launch ESPN app
  2. Scroll DOWN through ESPN home to find the NHL row
  3. Enter NHL row, screen-scrape visible game cards (~3 at a time)
  4. Go RIGHT 3 at a time to scroll new games into view
  5. When target team found, navigate to that specific card and select
  6. On game detail/hub page, find and select the specific game
  7. Hit Watch/Play to start stream
"""
import sys
import time
import re
import json
import os

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from apis.tv_control.fire_tv import _run_adb_command, _send_wol, FIRE_TV_MAC_ADDRESSES

ESPN_PKG = 'com.espn.gtv'
ESPN_ACTIVITY = f'{ESPN_PKG}/com.espn.startup.presentation.StartupActivity'
ADB_TIMEOUT = 30.0


def log(msg):
    print(f"[ESPN] {msg}", file=sys.stderr, flush=True)


def _adb(ip, cmd):
    """Run ADB command with retry. Fire TV ADB daemon gets sluggish during heavy apps."""
    for attempt in range(3):
        try:
            return _run_adb_command(ip, cmd, timeout=ADB_TIMEOUT)
        except Exception as e:
            if attempt < 2:
                log(f"ADB retry {attempt + 1} for '{cmd[:50]}': {e}")
                time.sleep(5)
            else:
                raise


def _dump_ui(ip):
    """Dump UI and return XML string."""
    _adb(ip, 'uiautomator dump /sdcard/ui.xml 2>&1')
    time.sleep(1)
    return _adb(ip, 'cat /sdcard/ui.xml')


def _get_screen_texts(xml):
    """Extract all visible text from UI XML — both text="" and content-desc="".

    ESPN Fire TV puts game info in content-desc (accessibility labels).
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


def _find_nhl_game_cards(texts):
    """Extract individual NHL game cards from screen texts.

    Game cards have content-desc like "ESPN+ • NHL Live Avalanche 4 Penguins 1 6:02 - 2nd"
    Returns list of (full_text, x1, y1, x2, y2) sorted by x position (left to right).
    """
    cards = []
    for t, x1, y1, x2, y2 in texts:
        # Individual game cards contain "NHL" and "Live" and team-like words
        # Filter out summary headers (contain "•" multiple times like "SEA vs. FLA • OTT vs. DET")
        if 'NHL' in t and 'Live' in t and t.count(' vs. ') <= 1:
            # Must look like a game card, not a section header
            if 'On Now' not in t and 'Stream over' not in t:
                cards.append((t, x1, y1, x2, y2))
    # Sort left to right
    cards.sort(key=lambda c: c[1])
    return cards


def _get_focused_element(xml):
    """Get the focused element's content-desc/text and bounds.

    Returns (desc_or_text, x1, y1, x2, y2) or None.
    """
    if not xml:
        return None

    # Try content-desc first (ESPN uses this for game cards)
    for pattern in [
        r'focused="true"[^>]*content-desc="([^"]+)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
        r'content-desc="([^"]+)"[^>]*focused="true"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
        r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"[^>]*focused="true"[^>]*content-desc="([^"]+)"',
        r'focused="true"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"[^>]*content-desc="([^"]+)"',
    ]:
        match = re.search(pattern, xml)
        if match:
            groups = match.groups()
            if len(groups) == 5:
                # Figure out which group is the text vs coordinates
                # Pattern varies — desc could be first or last
                try:
                    int(groups[0])
                    # First group is a number — desc is last
                    return (groups[4], int(groups[0]), int(groups[1]), int(groups[2]), int(groups[3]))
                except ValueError:
                    # First group is text
                    return (groups[0], int(groups[1]), int(groups[2]), int(groups[3]), int(groups[4]))

    # Fall back to text attribute
    for pattern in [
        r'focused="true"[^>]*text="([^"]+)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
        r'text="([^"]+)"[^>]*focused="true"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
    ]:
        match = re.search(pattern, xml)
        if match:
            return (match.group(1), int(match.group(2)), int(match.group(3)),
                    int(match.group(4)), int(match.group(5)))

    return None


def _wake_and_launch(ip):
    """Wake Fire TV and launch ESPN app."""
    mac = FIRE_TV_MAC_ADDRESSES.get(ip)
    if mac:
        log(f"Sending WoL to {ip} ({mac})")
        try:
            _send_wol(mac)
        except Exception:
            pass
        time.sleep(3)

    _adb(ip, 'input keyevent KEYCODE_WAKEUP')
    log("Sent WAKEUP")
    time.sleep(2)

    log("Force-stopping ESPN")
    _adb(ip, f'am force-stop {ESPN_PKG}')
    time.sleep(2)

    log("Launching ESPN app")
    _adb(ip, f'am start -n {ESPN_ACTIVITY}')
    log("Waiting 18s for ESPN to fully load...")
    time.sleep(18)


def _scroll_down_to_nhl(ip, max_downs=15):
    """Scroll DOWN through ESPN home screen until we find the NHL row.

    Returns True if NHL row found.
    """
    last_texts_key = None
    stuck_count = 0

    for i in range(max_downs):
        xml = _dump_ui(ip)
        texts = _get_screen_texts(xml)
        text_strs = [t for t, *_ in texts if len(t) > 1]
        log(f"DOWN {i}: {text_strs[:10]}")

        # Look for "NHL" as a section header (text attribute, not content-desc)
        for t, x1, y1, x2, y2 in texts:
            if t.strip().upper() == 'NHL':
                log(f"Found NHL header at y={y1}")
                return True

        # Stuck detection
        key = str(sorted(set(text_strs)))
        if key == last_texts_key:
            stuck_count += 1
            if stuck_count >= 3:
                log("Stuck — hit bottom of page")
                return False
        else:
            stuck_count = 0
            last_texts_key = key

        _adb(ip, 'input keyevent KEYCODE_DPAD_DOWN')
        time.sleep(1.5)

    return False


def _get_focused_bounds(xml):
    """Get bounds of the focused element."""
    if not xml:
        return None
    match = re.search(r'focused="true"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
    if not match:
        match = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"[^>]*focused="true"', xml)
    if match:
        return (int(match.group(1)), int(match.group(2)),
                int(match.group(3)), int(match.group(4)))
    return None


def _get_focused_game(xml):
    """Get the NHL game card that overlaps with the focused element.

    The ESPN app's focused element is a container with empty text/content-desc.
    The actual game info is in a child or sibling with content-desc set.
    We match by finding the content-desc whose bounds exactly overlap the focused bounds.
    """
    focused = _get_focused_bounds(xml)
    if not focused:
        return None, None
    fx1, fy1, fx2, fy2 = focused

    # Find content-desc elements whose bounds match the focused element exactly
    best_match = None
    best_overlap = 0
    for m in re.finditer(
        r'content-desc="([^"]+)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml
    ):
        desc = m.group(1)
        cx1, cy1, cx2, cy2 = int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5))
        # Calculate overlap area
        ox = max(0, min(fx2, cx2) - max(fx1, cx1))
        oy = max(0, min(fy2, cy2) - max(fy1, cy1))
        overlap = ox * oy
        if overlap > best_overlap and len(desc) > 10:
            best_overlap = overlap
            best_match = desc

    return best_match, focused


def _scan_nhl_row_for_team(ip, target_team):
    """Scan the NHL game row for the target team.

    Strategy:
      - Screen-scrape at current position
      - Check what game card the focus is actually on (overlap with focused bounds)
      - Also check all visible NHL game cards
      - If target visible: navigate RIGHT/LEFT from current focused card to target
      - If not visible: go RIGHT 3 to load next batch, re-scrape
      - Stuck detection: same focused game 3 times = end of row

    Returns True if game was found and selected.
    """
    target_lower = target_team.lower()
    last_focused_desc = None
    stuck_count = 0

    for batch in range(10):
        xml = _dump_ui(ip)
        texts = _get_screen_texts(xml)
        cards = _find_nhl_game_cards(texts)
        focused_desc, focused_bounds = _get_focused_game(xml)

        card_summaries = [c[0][:60] for c in cards]
        log(f"Batch {batch}: focused='{(focused_desc or 'None')[:60]}', {len(cards)} NHL cards")
        for c in card_summaries:
            log(f"  card: {c}")

        # Check if focus is already on our target
        if focused_desc and target_lower in focused_desc.lower():
            log(f"Focus IS on target! Selecting...")
            _adb(ip, 'input keyevent KEYCODE_DPAD_CENTER')
            log("Selected game card via CENTER")
            time.sleep(3)
            return True

        # Check if target is visible among the NHL cards
        target_card = None
        for t, x1, y1, x2, y2 in cards:
            if target_lower in t.lower():
                target_card = (t, x1, y1, x2, y2)
                break

        if target_card and focused_bounds:
            # Target is visible but not focused — navigate to it
            t_text, tx1, ty1, tx2, ty2 = target_card
            fx1, fy1, fx2, fy2 = focused_bounds

            if tx1 > fx1:
                # Target is to the RIGHT
                moves = max(1, (tx1 - fx1) // 400)
                log(f"Target '{target_team}' visible to RIGHT (target_x={tx1}, focus_x={fx1}), moving RIGHT {moves}")
                for _ in range(moves):
                    _adb(ip, 'input keyevent KEYCODE_DPAD_RIGHT')
                    time.sleep(1)
            elif tx1 < fx1:
                # Target is to the LEFT
                moves = max(1, (fx1 - tx1) // 400)
                log(f"Target '{target_team}' visible to LEFT (target_x={tx1}, focus_x={fx1}), moving LEFT {moves}")
                for _ in range(moves):
                    _adb(ip, 'input keyevent KEYCODE_DPAD_LEFT')
                    time.sleep(1)

            # Re-check if we're now on the target
            vxml = _dump_ui(ip)
            vdesc, _ = _get_focused_game(vxml)
            if vdesc and target_lower in vdesc.lower():
                log(f"Now focused on target! Selecting...")
                _adb(ip, 'input keyevent KEYCODE_DPAD_CENTER')
                log("Selected game card via CENTER")
                time.sleep(3)
                return True
            else:
                log(f"After navigation, focused on: '{(vdesc or 'None')[:60]}'")
                # Try one more RIGHT or LEFT
                _adb(ip, 'input keyevent KEYCODE_DPAD_RIGHT')
                time.sleep(1)
                vxml2 = _dump_ui(ip)
                vdesc2, _ = _get_focused_game(vxml2)
                if vdesc2 and target_lower in vdesc2.lower():
                    log(f"Found after extra RIGHT! Selecting...")
                    _adb(ip, 'input keyevent KEYCODE_DPAD_CENTER')
                    time.sleep(3)
                    return True
                # Try LEFT
                _adb(ip, 'input keyevent KEYCODE_DPAD_LEFT')
                time.sleep(1)
                _adb(ip, 'input keyevent KEYCODE_DPAD_LEFT')
                time.sleep(1)
                vxml3 = _dump_ui(ip)
                vdesc3, _ = _get_focused_game(vxml3)
                if vdesc3 and target_lower in vdesc3.lower():
                    log(f"Found after extra LEFT! Selecting...")
                    _adb(ip, 'input keyevent KEYCODE_DPAD_CENTER')
                    time.sleep(3)
                    return True

        # Stuck detection
        if focused_desc == last_focused_desc:
            stuck_count += 1
            if stuck_count >= 3:
                log("Same focused card 3x — end of row")
                return False
        else:
            stuck_count = 0
            last_focused_desc = focused_desc

        # Not found — scroll RIGHT 3 to get new batch
        log("Target not found in this batch, scrolling RIGHT 3")
        for _ in range(3):
            _adb(ip, 'input keyevent KEYCODE_DPAD_RIGHT')
            time.sleep(1)
        time.sleep(1)

    return False


def _select_game_on_hub(ip, target_team):
    """On the NHL hub/detail page, find and select the specific game.

    After selecting a game card from the NHL row, ESPN may show a hub page
    with a list of all NHL games. We need to find and select our specific game.
    """
    target_lower = target_team.lower()

    xml = _dump_ui(ip)
    texts = _get_screen_texts(xml)
    text_strs = [t for t, *_ in texts if len(t) > 1]
    log(f"Hub page: {text_strs[:15]}")

    # Check if we landed directly on a game page (has Watch/Play button)
    watch_keywords = {'watch', 'watch live', 'watch now', 'go live', 'resume', 'play',
                      'start from beginning', 'catch up to live', 'watch live with stats'}
    has_watch = any(t.lower().strip() in watch_keywords for t, *_ in texts)
    if has_watch:
        log("Already on game page — using watch button selector")
        return _select_watch_button(ip)

    # We're on a hub page with a list of games — use D-pad to navigate
    # Find all game entries with their y-positions
    game_entries = []
    for t, x1, y1, x2, y2 in texts:
        if ('vs.' in t or 'Live' in t) and 'NHL' in t and 'Stream over' not in t:
            game_entries.append((t, x1, y1, x2, y2))
    game_entries.sort(key=lambda g: g[2])  # Sort by y position

    log(f"Hub game entries: {[g[0][:50] for g in game_entries]}")

    # Find which entry has our team
    target_idx = None
    for idx, (t, *_rest) in enumerate(game_entries):
        if target_lower in t.lower():
            target_idx = idx
            log(f"Target game is entry {idx}: {t[:60]}")
            break

    if target_idx is not None:
        # Navigate DOWN to the target game entry
        # First DOWN gets us from the header into the list
        _adb(ip, 'input keyevent KEYCODE_DPAD_DOWN')
        time.sleep(1)

        # Then DOWN to reach the target entry
        for _ in range(target_idx):
            _adb(ip, 'input keyevent KEYCODE_DPAD_DOWN')
            time.sleep(0.8)

        # CENTER to select the game
        _adb(ip, 'input keyevent KEYCODE_DPAD_CENTER')
        log(f"Selected game entry {target_idx}")
        time.sleep(4)

        # Extra CENTER to start watching live
        _adb(ip, 'input keyevent KEYCODE_DPAD_CENTER')
        log("Extra CENTER to watch live")
        time.sleep(3)
        return True

    # Game not visible — scroll down to find it
    for scroll in range(8):
        _adb(ip, 'input keyevent KEYCODE_DPAD_DOWN')
        time.sleep(1)

        xml = _dump_ui(ip)
        texts = _get_screen_texts(xml)
        for t, x1, y1, x2, y2 in texts:
            if target_lower in t.lower() and ('vs.' in t or 'Live' in t):
                log(f"Found game after {scroll+1} downs: '{t[:60]}'")
                _adb(ip, 'input keyevent KEYCODE_DPAD_CENTER')
                log("Selected game entry")
                time.sleep(4)
                return _select_watch_button(ip)

    # Fallback: press CENTER on whatever is focused
    _adb(ip, 'input keyevent KEYCODE_DPAD_CENTER')
    log("Pressed CENTER as fallback on hub page")
    time.sleep(3)
    return _select_watch_button(ip)


def _select_watch_button(ip):
    """On the game page, find and select Watch Live (preferred) or other watch options.

    After tapping, verifies the stream actually started. If watch buttons are
    still visible, retries the tap. Returns False if stream didn't start after
    multiple attempts (caller should use resilient restart).
    """
    WATCH_PRIORITY = [
        'watch live', 'go live', 'watch now', 'watch', 'resume',
        'catch up to live', 'play', 'start from beginning'
    ]
    WATCH_SET = set(WATCH_PRIORITY)

    def _find_best_watch(texts):
        for keyword in WATCH_PRIORITY:
            for t, x1, y1, x2, y2 in texts:
                if t.lower().strip() == keyword:
                    return (t, x1, y1, x2, y2)
        return None

    def _has_watch_buttons(texts):
        return any(t.lower().strip() in WATCH_SET for t, *_ in texts)

    for attempt in range(3):
        xml = _dump_ui(ip)
        texts = _get_screen_texts(xml)
        text_strs = [t for t, *_ in texts if len(t) > 1]
        log(f"Watch attempt {attempt}: {text_strs[:15]}")

        best = _find_best_watch(texts)
        if not best:
            # Try scrolling down to find it
            for _ in range(3):
                _adb(ip, 'input keyevent KEYCODE_DPAD_DOWN')
                time.sleep(1)
            xml = _dump_ui(ip)
            texts = _get_screen_texts(xml)
            best = _find_best_watch(texts)

        if best:
            t, x1, y1, x2, y2 = best
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            _adb(ip, f'input tap {cx} {cy}')
            log(f"Tapped '{t}' at ({cx},{cy})")
            time.sleep(5)

            # Verify: if watch buttons are gone, stream started
            verify_xml = _dump_ui(ip)
            verify_texts = _get_screen_texts(verify_xml)
            if not _has_watch_buttons(verify_texts):
                log("Stream started — watch buttons are gone")
                return True
            else:
                log(f"Watch buttons still visible after tap, retrying...")
                # Try CENTER press as well
                _adb(ip, 'input keyevent KEYCODE_DPAD_CENTER')
                time.sleep(5)
                verify_xml2 = _dump_ui(ip)
                verify_texts2 = _get_screen_texts(verify_xml2)
                if not _has_watch_buttons(verify_texts2):
                    log("Stream started after CENTER press")
                    return True
        else:
            # No watch buttons found — maybe stream already started
            log("No watch buttons found — stream may already be playing")
            return True

    log("Failed to start stream after 3 attempts")
    return False


def _reset_to_espn_home(ip):
    """Reset to ESPN home screen — known good starting point."""
    log("Resetting to ESPN home...")
    _adb(ip, f'am force-stop {ESPN_PKG}')
    time.sleep(2)
    _adb(ip, f'am start -n {ESPN_ACTIVITY}')
    log("Waiting 18s for ESPN to reload...")
    time.sleep(18)


def launch_game(ip, away_team, home_team):
    target_team = away_team or home_team
    other_team = home_team if target_team == away_team else away_team

    for attempt in range(3):
        if attempt > 0:
            log(f"=== RETRY {attempt} — resetting to ESPN home ===")
            _reset_to_espn_home(ip)
        else:
            # Phase 1: Wake + launch ESPN
            _wake_and_launch(ip)

        # Phase 2: Scroll DOWN to find NHL row
        found_nhl = _scroll_down_to_nhl(ip)
        if not found_nhl:
            log("Could not find NHL section, will retry")
            continue

        # Phase 3: Enter the NHL game cards row
        # The NHL section has multiple sub-rows. Keep pressing DOWN until
        # the focused element overlaps with an NHL game card.
        log("Navigating DOWN into NHL game cards...")
        for down_attempt in range(5):
            _adb(ip, 'input keyevent KEYCODE_DPAD_DOWN')
            time.sleep(1.5)
            xml = _dump_ui(ip)
            focused_desc, _ = _get_focused_game(xml)
            log(f"  DOWN {down_attempt}: focused='{(focused_desc or 'None')[:60]}'")
            if focused_desc and 'NHL' in focused_desc:
                log("Focus is on an NHL game card!")
                break

        # Phase 4: Scan RIGHT through NHL games for our team
        found_team = _scan_nhl_row_for_team(ip, target_team)
        if not found_team and other_team:
            log(f"'{target_team}' not found, trying '{other_team}'")
            # Go all the way LEFT to reset to start of row
            for _ in range(25):
                _adb(ip, 'input keyevent KEYCODE_DPAD_LEFT')
                time.sleep(0.3)
            time.sleep(1)
            found_team = _scan_nhl_row_for_team(ip, other_team)
            if found_team:
                target_team = other_team

        if not found_team:
            log("Team not found in NHL row, will retry")
            continue

        # Phase 5: On game detail/hub page, find specific game and watch
        if _select_game_on_hub(ip, target_team):
            return {'success': True, 'team': target_team, 'method': 'screen_scrape'}
        else:
            log("Could not start stream, will retry")
            continue

    return {'error': f'Could not find or launch {away_team} vs {home_team} after 3 attempts'}


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print(json.dumps({'error': 'Usage: espn_launcher.py <ip> <away_team> <home_team>'}))
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
