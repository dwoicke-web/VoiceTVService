#!/usr/bin/env python3
"""Standalone ESPN+ game launcher for Fire TV.

Run as a subprocess to avoid ADB connection contention.
Usage: python3 espn_launcher.py <fire_tv_ip> <away_team> <home_team>

Exits 0 on success, 1 on failure. Prints JSON result to stdout.

Strategy:
  1. Wake Fire TV, launch ESPN app
  2. Scroll DOWN through ESPN home to find the league row (e.g. NHL)
     - If direct league row not found but "Leagues" row exists, use fallback:
       navigate RIGHT on Leagues row to find the league, select it,
       then find "Live & Upcoming" row on the league page
  3. Enter game cards row, screen-scrape visible cards (~3 at a time)
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
from debug_logging.step_logger import start_run, log_step, get_current_run_id
from debug_logging import run_storage

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


def _scroll_down_to_nhl(ip, league='NHL', max_downs=15):
    """Scroll DOWN through ESPN home screen until we find the league row.

    Returns 'league_row' if the direct league row (e.g. NHL) is found,
    'leagues_row' if a generic "Leagues" row is found first (fallback path),
    or 'not_found'.
    """
    log(f"\n========== PHASE 1: SCROLL DOWN TO FIND {league} ROW ==========")
    last_texts_key = None
    stuck_count = 0
    league_upper = league.strip().upper()

    for i in range(max_downs):
        log(f"\n--- DOWN iteration {i} ---")
        xml = _dump_ui(ip)
        texts = _get_screen_texts(xml)
        text_strs = [t for t, *_ in texts if len(t) > 1]

        log(f"Screen contains {len(texts)} elements, showing all:")
        for j, (t, x1, y1, x2, y2) in enumerate(texts[:25]):
            log(f"  [{j:2d}] y={y1:4d} '{t[:50]}'")

        # Check for league row
        found_league = False
        found_leagues = False
        for t, x1, y1, x2, y2 in texts:
            t_upper = t.strip().upper()
            # Look for the specific league as a section header
            if t_upper == league_upper:
                log(f"✓ SUCCESS: Found '{league}' header row at y={y1}")
                return 'league_row'
            # Look for generic "Leagues" row as fallback
            if t_upper == 'LEAGUES':
                log(f"⚠ FALLBACK: Found 'Leagues' row at y={y1}")
                return 'leagues_row'

        log(f"✗ No '{league}' or 'Leagues' row found in this screen")

        # Stuck detection
        key = str(sorted(set(text_strs)))
        if key == last_texts_key:
            stuck_count += 1
            log(f"⚠ Screen unchanged {stuck_count} times (stuck detection)")
            if stuck_count >= 3:
                log(f"✗ FAILURE: Stuck for {stuck_count} iterations — hit bottom of page")
                return 'not_found'
        else:
            stuck_count = 0
            last_texts_key = key
            log(f"✓ Screen changed, reset stuck counter")

        log(f"Pressing DOWN...")
        _adb(ip, 'input keyevent KEYCODE_DPAD_DOWN')
        time.sleep(1.5)

    log(f"\n✗ FAILURE: Reached max DOWN iterations ({max_downs}) without finding {league} row")
    return 'not_found'


def _navigate_leagues_to_league(ip, league='NHL', max_rights=15):
    """On the 'Leagues' row, scroll RIGHT to find and select the target league.

    After selecting, ESPN navigates to a league-specific page.
    Returns True if the league was found and selected.
    """
    log(f"\n========== PHASE 2: NAVIGATE LEAGUES ROW TO FIND {league.upper()} ==========")
    league_lower = league.strip().lower()

    # The "Leagues" label is visible but focus is still on the row above.
    # Scroll DOWN twice to get past the label and into the circle tiles row.
    log("Step 1: Scrolling DOWN 2x to get into Leagues circle tiles row...")
    for down_step in range(1, 3):
        log(f"  DOWN {down_step}/2")
        _adb(ip, 'input keyevent KEYCODE_DPAD_DOWN')
        time.sleep(1.5)
    log("Step 1 complete: Now in Leagues circle tiles row\n")

    last_focused = None
    stuck_count = 0

    for i in range(max_rights):
        log(f"\n========== RIGHT iteration {i}/{max_rights} ==========")
        xml = _dump_ui(ip)
        texts = _get_screen_texts(xml)
        text_strs = [t for t, *_ in texts if len(t) > 1]
        focused = _get_focused_element(xml)
        focused_text = focused[0] if focused else None

        log(f"SCREEN STATE:")
        log(f"  Currently focused: '{focused_text}'")
        if focused:
            fx1, fy1, fx2, fy2 = focused[1], focused[2], focused[3], focused[4]
            log(f"  Focus bounds: x1={fx1}, y1={fy1}, x2={fx2}, y2={fy2}")

        log(f"VISIBLE ELEMENTS ({len(texts)} total, showing up to 25):")
        for j, (t, x1, y1, x2, y2) in enumerate(texts[:25]):
            marker = ">>> " if focused and fx1 == x1 else "    "
            log(f"  {marker}[{j:2d}] x={x1:4d}-{x2:4d} y={y1:4d}-{y2:4d} '{t[:40]}'")

        log(f"\nEVALUATION:")

        # Check if the focused element or any visible text matches the league
        log(f"  Check 1: Is currently focused element '{league}'?")
        if focused_text and league_lower in focused_text.lower():
            log(f"    ✓ YES! '{focused_text}' contains '{league}' — SELECTING NOW")
            _adb(ip, 'input keyevent KEYCODE_DPAD_CENTER')
            time.sleep(4)
            return True
        else:
            log(f"    ✗ NO (focused='{focused_text}')")

        # Also check all visible texts for the league name as a selectable item
        log(f"  Check 2: Is '{league}' visible anywhere on screen?")
        league_tile = None
        for t, x1, y1, x2, y2 in texts:
            if t.strip().upper() == league.strip().upper():
                log(f"    ✓ YES! Found '{league}' text at x={x1}, y={y1}")
                league_tile = (t, x1, y1, x2, y2)
                break

        if not league_tile:
            log(f"    ✗ NO ('{league}' not on screen)")

        if league_tile:
            t_text, tx1, ty1, tx2, ty2 = league_tile

            log(f"\n  Check 3: Can we navigate to '{league}'?")
            log(f"    {league.upper()} tile: x1={tx1}, x2={tx2}, y1={ty1}, y2={ty2}")

            # Calculate distance if we have a focused element, otherwise just navigate to league position
            if focused:
                fx1, fy1, fx2, fy2 = focused[1], focused[2], focused[3], focused[4]
                log(f"    Focus circle:   x1={fx1}, x2={fx2}, y1={fy1}, y2={fy2}")

                # Calculate distance from focus center to league tile center
                focus_center = fx1 + (fx2 - fx1) // 2
                league_center = tx1 + (tx2 - tx1) // 2
                distance = league_center - focus_center

                log(f"    Distance calculation:")
                log(f"      {league.upper()} center: x={league_center}")
                log(f"      Focus center: x={focus_center}")
                log(f"      Δ distance: {distance} pixels")
            else:
                log(f"    No focus element yet, will navigate based on league position")
                # Center of league tile
                league_center = tx1 + (tx2 - tx1) // 2
                # Assume focus starts around screen center
                focus_center = 960  # Fire TV width is 1920, center is 960
                distance = league_center - focus_center
                log(f"    Estimated distance: {distance} pixels (assuming center focus)")

            # If league tile is not at focus position, navigate to it step by step with verification
            if abs(distance) > 50:  # Some tolerance for overlap
                direction = "RIGHT" if distance > 0 else "LEFT"
                abs_distance = abs(distance)

                # Conservative: move 1 step at a time, verify after each step
                log(f"\n  NAVIGATION SEQUENCE:")
                log(f"    {league.upper()} is {abs_distance}px to the {direction}")
                log(f"    Starting step-by-step navigation (max 8 steps, 1 at a time)...")

                found_league = False
                for step in range(1, 9):  # Max 8 steps to avoid overshooting
                    if found_league:
                        break

                    log(f"      Step {step}/8: Press {direction}")
                    if direction == "RIGHT":
                        _adb(ip, 'input keyevent KEYCODE_DPAD_RIGHT')
                    else:
                        _adb(ip, 'input keyevent KEYCODE_DPAD_LEFT')
                    time.sleep(0.8)

                    # Check what's focused now
                    xml_check = _dump_ui(ip)
                    focused_check = _get_focused_element(xml_check)
                    focused_text_check = focused_check[0] if focused_check else None

                    # Get all visible leagues to show context
                    texts_check = _get_screen_texts(xml_check)
                    visible_leagues = [t for t, *_ in texts_check if any(league in t.upper() for league in ['NHL', 'NFL', 'NBA', 'NWSL', 'MLS'])]

                    log(f"           Result: focused='{focused_text_check}'")
                    if visible_leagues:
                        log(f"           Visible leagues: {', '.join(visible_leagues[:10])}")

                    # If we landed on the league, stop navigating
                    if focused_text_check and league_lower in focused_text_check.lower():
                        log(f"      ✓ FOUND! Successfully focused on '{league}' after {step} step(s)")
                        found_league = True
                        time.sleep(1)
                        break

                    # If we overshot and are on something else, try going back
                    if step >= 2 and focused_text_check and league_lower not in focused_text_check.lower():
                        back_direction = "LEFT" if direction == "RIGHT" else "RIGHT"
                        log(f"      ⚠ OVERSHOOT DETECTED: Now on '{focused_text_check}' (not '{league}')")
                        log(f"      Attempting recovery with {back_step} steps in {back_direction} direction...")
                        for back_step in range(1, 5):
                            log(f"        Back-step {back_step}/4: Press {back_direction}")
                            if back_direction == "LEFT":
                                _adb(ip, 'input keyevent KEYCODE_DPAD_LEFT')
                            else:
                                _adb(ip, 'input keyevent KEYCODE_DPAD_RIGHT')
                            time.sleep(0.8)

                            xml_back = _dump_ui(ip)
                            focused_back = _get_focused_element(xml_back)
                            focused_text_back = focused_back[0] if focused_back else None
                            log(f"             Result: focused='{focused_text_back}'")

                            if focused_text_back and league_lower in focused_text_back.lower():
                                log(f"        ✓ FOUND! '{league}' after backing up")
                                found_league = True
                                break
                        if found_league:
                            break
            else:
                log(f"\n  Check 3: Distance analysis")
                log(f"    {league.upper()} is within 50px of focus, no navigation needed")

            # Final verification before selecting
            log(f"\n  FINAL VERIFICATION:")
            xml_final = _dump_ui(ip)
            focused_final = _get_focused_element(xml_final)
            focused_text_final = focused_final[0] if focused_final else None
            log(f"    Current focus: '{focused_text_final}'")
            log(f"    Expected: '{league}'")

            if not (focused_text_final and league_lower in focused_text_final.lower()):
                log(f"    ✗ MISMATCH! Not on '{league}' — skipping select, continuing RIGHT")
                _adb(ip, 'input keyevent KEYCODE_DPAD_RIGHT')
                time.sleep(1)
                continue

            # Now select it
            log(f"    ✓ MATCH! Focus confirmed on '{league}'")
            log(f"\n  ACTION: Selecting '{league}' league via CENTER keyevent")
            _adb(ip, 'input keyevent KEYCODE_DPAD_CENTER')
            time.sleep(4)
            log(f"  ✓ SUCCESS: {league} league selected and ESPN navigating to league page")
            return True

        # Continue pressing RIGHT if no league tile found
        log(f"\n  NO {league.upper()} TILE ON SCREEN:")

        # Stuck detection: only give up after 8+ consecutive iterations with no focus change
        if focused_text == last_focused:
            stuck_count += 1
            log(f"    Stuck detection: same focus '{focused_text}' for {stuck_count}/8 iterations")
            if stuck_count >= 8:
                log(f"    ✗ FAILURE: Stuck for 8 iterations — cannot find '{league}'")
                return False
        else:
            stuck_count = 0
            last_focused = focused_text
            log(f"    Focus changed, reset stuck counter")

        log(f"    ACTION: Pressing RIGHT to continue searching...")
        _adb(ip, 'input keyevent KEYCODE_DPAD_RIGHT')
        time.sleep(1)

    log(f"\n✗ FAILURE: Reached max RIGHT iterations ({max_rights}) without finding '{league}'")
    return False


def _find_and_scan_live_upcoming(ip, target_team, max_downs=10):
    """After selecting a league from the Leagues row, find 'Live & Upcoming'
    row and scan it for the target game.

    Uses the same batch-scanning behavior: take a snapshot, examine visible
    cards, if target not found go RIGHT 3 and repeat.

    Returns True if the game was found and selected.
    """
    target_lower = target_team.lower()

    # Scroll DOWN to find the "Live & Upcoming" row
    last_texts_key = None
    stuck_count = 0

    for i in range(max_downs):
        xml = _dump_ui(ip)
        texts = _get_screen_texts(xml)
        text_strs = [t for t, *_ in texts if len(t) > 1]
        log(f"League page DOWN {i}: {text_strs[:10]}")

        for t, x1, y1, x2, y2 in texts:
            if 'live' in t.lower() and 'upcoming' in t.lower():
                log(f"Found 'Live & Upcoming' row at y={y1}")
                # Navigate DOWN into the row items
                _adb(ip, 'input keyevent KEYCODE_DPAD_DOWN')
                time.sleep(1.5)
                return _scan_row_for_team(ip, target_team)

        # Stuck detection
        key = str(sorted(set(text_strs)))
        if key == last_texts_key:
            stuck_count += 1
            if stuck_count >= 3:
                log("Stuck — could not find 'Live & Upcoming' row")
                return False
        else:
            stuck_count = 0
            last_texts_key = key

        _adb(ip, 'input keyevent KEYCODE_DPAD_DOWN')
        time.sleep(1.5)

    log("'Live & Upcoming' row not found after max scrolls")
    return False


def _scan_row_for_team(ip, target_team, max_batches=10):
    """Scan current row RIGHT for the target team using batch-scraping.

    Same strategy as _scan_nhl_row_for_team: snapshot, examine visible game
    cards, if target not found go RIGHT 3 to load next batch, re-scrape.
    Stuck detection: same focused element 3 times = end of row.

    Returns True if game was found and selected.
    """
    target_lower = target_team.lower()
    last_focused_desc = None
    stuck_count = 0

    for batch in range(max_batches):
        xml = _dump_ui(ip)
        texts = _get_screen_texts(xml)
        focused = _get_focused_element(xml)
        focused_desc = focused[0] if focused else None
        focused_bounds = (focused[1], focused[2], focused[3], focused[4]) if focused else None

        text_strs = [t for t, *_ in texts if len(t) > 1]
        log(f"Row scan batch {batch}: focused='{(focused_desc or 'None')[:60]}', visible={text_strs[:8]}")

        # Check if focus is already on our target
        if focused_desc and target_lower in focused_desc.lower():
            log(f"Focus IS on target! Selecting...")
            _adb(ip, 'input keyevent KEYCODE_DPAD_CENTER')
            time.sleep(3)
            return True

        # Check all visible texts for the target team
        target_card = None
        for t, x1, y1, x2, y2 in texts:
            if target_lower in t.lower() and len(t) > 10:
                target_card = (t, x1, y1, x2, y2)
                break

        if target_card and focused_bounds:
            # Target is visible but not focused — navigate to it
            t_text, tx1, ty1, tx2, ty2 = target_card
            fx1, fy1, fx2, fy2 = focused_bounds

            if tx1 > fx1:
                moves = max(1, (tx1 - fx1) // 400)
                log(f"Target visible to RIGHT, moving RIGHT {moves}")
                for _ in range(moves):
                    _adb(ip, 'input keyevent KEYCODE_DPAD_RIGHT')
                    time.sleep(1)
            elif tx1 < fx1:
                moves = max(1, (fx1 - tx1) // 400)
                log(f"Target visible to LEFT, moving LEFT {moves}")
                for _ in range(moves):
                    _adb(ip, 'input keyevent KEYCODE_DPAD_LEFT')
                    time.sleep(1)

            # Verify focus is on target
            vxml = _dump_ui(ip)
            vfocused = _get_focused_element(vxml)
            vdesc = vfocused[0] if vfocused else None
            if vdesc and target_lower in vdesc.lower():
                log(f"Now focused on target! Selecting...")
                _adb(ip, 'input keyevent KEYCODE_DPAD_CENTER')
                time.sleep(3)
                return True
            else:
                log(f"After navigation, focused on: '{(vdesc or 'None')[:60]}'")
                # Try one more RIGHT
                _adb(ip, 'input keyevent KEYCODE_DPAD_RIGHT')
                time.sleep(1)
                vxml2 = _dump_ui(ip)
                vfocused2 = _get_focused_element(vxml2)
                vdesc2 = vfocused2[0] if vfocused2 else None
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
                vfocused3 = _get_focused_element(vxml3)
                vdesc3 = vfocused3[0] if vfocused3 else None
                if vdesc3 and target_lower in vdesc3.lower():
                    log(f"Found after extra LEFT! Selecting...")
                    _adb(ip, 'input keyevent KEYCODE_DPAD_CENTER')
                    time.sleep(3)
                    return True

        # Stuck detection
        if focused_desc == last_focused_desc:
            stuck_count += 1
            if stuck_count >= 3:
                log("Same focused element 3x — end of row")
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


def launch_game(ip, away_team, home_team, league='NHL', _run_id=None):
    """Launch a game on ESPN+ Fire TV."""
    # Initialize logging run if not already started
    if _run_id is None:
        _run_id = start_run({
            'type': 'espn_launcher',
            'ip': ip,
            'away_team': away_team,
            'home_team': home_team,
            'league': league,
            'status': 'in_progress',
        })

    target_team = away_team or home_team
    other_team = home_team if target_team == away_team else away_team

    result = None
    try:
        for attempt in range(3):
            if attempt > 0:
                log(f"=== RETRY {attempt} — resetting to ESPN home ===")
                _reset_to_espn_home(ip)
            else:
                # Phase 1: Wake + launch ESPN
                _wake_and_launch(ip)

            # Phase 2: Scroll DOWN to find league row (or fallback Leagues row)
            scroll_result = _scroll_down_to_nhl(ip, league=league)
            if scroll_result == 'not_found':
                log(f"Could not find {league} section or Leagues row, will retry")
                continue

            found_team = False

            if scroll_result == 'leagues_row':
                # Fallback path: use the Leagues row to navigate to the league
                log(f"Using Leagues row fallback to find {league}...")
                if not _navigate_leagues_to_league(ip, league=league):
                    log(f"Could not find {league} in Leagues row, will retry")
                    continue

                # Now on the league page — find "Live & Upcoming" and scan for game
                found_team = _find_and_scan_live_upcoming(ip, target_team)
                if not found_team and other_team:
                    log(f"'{target_team}' not found, trying '{other_team}'")
                    # Go back and retry with the other team name
                    # Reset LEFT to start of row
                    for _ in range(25):
                        _adb(ip, 'input keyevent KEYCODE_DPAD_LEFT')
                        time.sleep(0.3)
                    time.sleep(1)
                    found_team = _scan_row_for_team(ip, other_team)
                    if found_team:
                        target_team = other_team

            else:
                # Direct league row found (e.g. "NHL" header on home screen)
                # Phase 3: Enter the league game cards row
                log(f"Navigating DOWN into {league} game cards...")
                for down_attempt in range(5):
                    _adb(ip, 'input keyevent KEYCODE_DPAD_DOWN')
                    time.sleep(1.5)
                    xml = _dump_ui(ip)
                    focused_desc, _ = _get_focused_game(xml)
                    log(f"  DOWN {down_attempt}: focused='{(focused_desc or 'None')[:60]}'")
                    if focused_desc and league in focused_desc:
                        log(f"Focus is on a {league} game card!")
                        break

                # Phase 4: Scan RIGHT through games for our team
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
                log(f"Team not found in {league} row, will retry")
                continue

            # Phase 5: On game detail/hub page, find specific game and watch
            if _select_game_on_hub(ip, target_team):
                result = {'success': True, 'team': target_team, 'method': 'screen_scrape'}
                return result
            else:
                log("Could not start stream, will retry")
                continue

        result = {'error': f'Could not find or launch {away_team} vs {home_team} after 3 attempts'}
        return result
    finally:
        # Save run metadata with result
        if _run_id:
            # Log the overall execution as a step
            log_step(
                'launch_game',
                {'ip': ip, 'away_team': away_team, 'home_team': home_team, 'league': league},
                result,
                status='success' if (result and 'success' in result) else 'failure',
                duration=0
            )

            # Get the steps from the in-memory run
            run_data = get_run(_run_id)
            steps = run_data.get('steps', []) if run_data else []

            run_metadata = {
                'type': 'espn_launcher',
                'ip': ip,
                'away_team': away_team,
                'home_team': home_team,
                'league': league,
                'status': 'success' if (result and 'success' in result) else 'failure',
                'result': result,
            }
            run_storage.save_run(_run_id, steps, metadata=run_metadata)


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
