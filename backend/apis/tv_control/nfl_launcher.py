#!/usr/bin/env python3
"""Standalone NFL game launcher for Fire TV — navigates YouTube TV's on-screen
"NFL" content row (used for NFL Sunday Ticket / out-of-market games that don't
resolve to a direct-tune channel; national broadcasts on NBC/CBS/ABC/FOX/ESPN
are handled separately by fire_tv.tune_channel's deep-link path and never
reach this launcher).

Run as a subprocess to avoid ADB connection contention.
Usage: python3 nfl_launcher.py <fire_tv_ip> <away_team> <home_team>

Exits 0 on success, 1 on failure. Prints JSON result to stdout.

Strategy: YouTube TV's Fire TV app renders through Google's Cobalt (GL canvas)
runtime, which exposes NO accessibility tree — `uiautomator dump` returns an
empty grid of generic placeholder nodes regardless of what's on screen. This
is fundamentally different from the native-Android MLB/ESPN apps, so this
launcher reads the screen via screenshot + OCR instead:
  1. Launch YouTube TV to its home screen
  2. Press DOWN repeatedly, OCR-checking the row header text each time,
     until the "NFL" row is found
  3. Reset horizontal position to the start of the row (many LEFT presses)
  4. OCR the caption band under the row's tiles — every tile shows its own
     team-name caption underneath it regardless of focus, so all visible
     games can be read in one pass without needing to detect focus first.
     Step RIGHT to bring the target game into the row's fixed left-hand
     ("focused") slot, verifying by re-OCR after each move.
  5. Press CENTER to select, then OCR the following screen(s) for a
     Watch/Play-style control and select that too.
"""
import sys
import time
import re
import json
import os
import subprocess
import io
import asyncio

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from apis.tv_control.fire_tv import _run_adb_command, _send_wol, _wait_for_adb_ready, FIRE_TV_MAC_ADDRESSES, FireTVDevice
from debug_logging.step_logger import start_run, log_step
from debug_logging import run_storage

from PIL import Image
import numpy as np
import pytesseract

YTV_PKG = 'com.amazon.firetv.youtube.tv'
YTV_ACTIVITY = f'{YTV_PKG}/dev.cobalt.app.MainActivity'
ADB_TIMEOUT = 30.0

# Row/tile layout measured against the Fire TV Stick 4K's 1920x1080 output
# (same hardware + app build across all four TVs). Tiles sit on a fixed
# horizontal pitch starting at the row's left margin; captions render below
# every tile regardless of focus state, so team names can be read without
# ever needing to detect which tile currently has focus.
TILE_LEFT_X0 = 88
TILE_PITCH = 592
TILE_CAPTION_WIDTH = 560
CAPTION_Y0 = 620
CAPTION_Y1 = 800
HEADER_CROP = (80, 200, 500, 290)
NUM_VISIBLE_COLUMNS = 4  # ~3 full + 1 partial visible at 1920 width

NFL_TEAMS = {
    'bears', 'bengals', 'bills', 'broncos', 'browns', 'buccaneers', 'cardinals',
    'chargers', 'chiefs', 'colts', 'commanders', 'cowboys', 'dolphins', 'eagles',
    'falcons', 'giants', '49ers', 'niners', 'jaguars', 'jets', 'lions', 'packers',
    'panthers', 'patriots', 'raiders', 'rams', 'ravens', 'saints', 'seahawks',
    'steelers', 'texans', 'titans', 'vikings',
}

# Map city/abbreviation/alternate names to the team nickname
NFL_TEAM_ALIASES = {
    'sf': '49ers', 'san francisco': '49ers',
    'kc': 'chiefs', 'kansas city': 'chiefs',
    'ne': 'patriots', 'new england': 'patriots',
    'no': 'saints', 'new orleans': 'saints',
    'tb': 'buccaneers', 'tampa bay': 'buccaneers', 'bucs': 'buccaneers',
    'lv': 'raiders', 'las vegas': 'raiders', 'oak': 'raiders', 'oakland': 'raiders',
    'lar': 'rams', 'la rams': 'rams', 'los angeles rams': 'rams',
    'lac': 'chargers', 'la chargers': 'chargers', 'los angeles chargers': 'chargers',
    'sd': 'chargers', 'san diego': 'chargers',
    'gb': 'packers', 'green bay': 'packers',
    'jax': 'jaguars', 'jacksonville': 'jaguars',
    'ny giants': 'giants', 'nyg': 'giants', 'new york giants': 'giants',
    'ny jets': 'jets', 'nyj': 'jets', 'new york jets': 'jets',
    'wsh': 'commanders', 'washington': 'commanders', 'was': 'commanders',
    'ari': 'cardinals', 'arizona': 'cardinals',
    'atl': 'falcons', 'atlanta': 'falcons',
    'bal': 'ravens', 'baltimore': 'ravens',
    'buf': 'bills', 'buffalo': 'bills',
    'car': 'panthers', 'carolina': 'panthers',
    'chi': 'bears', 'chicago': 'bears',
    'cin': 'bengals', 'cincinnati': 'bengals',
    'cle': 'browns', 'cleveland': 'browns',
    'dal': 'cowboys', 'dallas': 'cowboys',
    'den': 'broncos', 'denver': 'broncos',
    'det': 'lions', 'detroit': 'lions',
    'hou': 'texans', 'houston': 'texans',
    'ind': 'colts', 'indianapolis': 'colts',
    'mia': 'dolphins', 'miami': 'dolphins',
    'min': 'vikings', 'minnesota': 'vikings',
    'phi': 'eagles', 'philadelphia': 'eagles',
    'pit': 'steelers', 'pittsburgh': 'steelers',
    'sea': 'seahawks', 'seattle': 'seahawks',
    'ten': 'titans', 'tennessee': 'titans',
}


def _normalize_team(name):
    """Normalize a team name/abbreviation to a single canonical nickname.

    Alias lookup runs before the direct NFL_TEAMS check, same as
    mlb_launcher.py's _normalize_team, so abbreviations canonicalize
    consistently even when they overlap a full-name entry.
    """
    lower = name.strip().lower()
    if lower in NFL_TEAM_ALIASES:
        return NFL_TEAM_ALIASES[lower]
    if lower in NFL_TEAMS:
        return lower
    for team in NFL_TEAMS:
        if lower in team or team in lower:
            return team
    for alias, team in NFL_TEAM_ALIASES.items():
        if lower in alias or alias in lower:
            return team
    return lower


def _team_matches(target_team, ocr_text):
    """True if the OCR'd caption text canonicalizes to the target team.

    Checks individual words first (captions are short, e.g. "Chicago Bears"),
    then falls back to the whole cleaned string for multi-word city names
    that a word-by-word split would break apart (e.g. "san francisco").
    """
    clean = re.sub(r'[^a-zA-Z0-9 ]', ' ', ocr_text).lower()
    for word in clean.split():
        if len(word) > 2 and _normalize_team(word) == target_team:
            return True
    return _normalize_team(clean.strip()) == target_team


def log(msg):
    print(f"[NFL] {msg}", file=sys.stderr, flush=True)


def _adb(ip, cmd):
    """Run ADB command with retry. Fire TV ADB daemon gets sluggish during heavy apps."""
    for attempt in range(5):
        try:
            return _run_adb_command(ip, cmd, timeout=ADB_TIMEOUT)
        except Exception as e:
            if attempt < 4:
                delay = 5 + attempt * 2
                log(f"ADB retry {attempt + 1} for '{cmd[:50]}': {e} (wait {delay}s)")
                time.sleep(delay)
            else:
                raise


def _screenshot(ip):
    """Capture the current screen as a PIL Image.

    Binary-safe, unlike _run_adb_command (which decodes as text and would
    corrupt PNG bytes) — shells out to adb directly instead.
    """
    try:
        result = subprocess.run(
            ['adb', '-s', f'{ip}:5555', 'exec-out', 'screencap', '-p'],
            capture_output=True, timeout=15
        )
        if not result.stdout:
            return None
        return Image.open(io.BytesIO(result.stdout))
    except Exception as e:
        log(f"Screenshot failed: {e}")
        return None


def _ocr(img_crop):
    """OCR a cropped region, returning the raw text."""
    try:
        return pytesseract.image_to_string(img_crop)
    except Exception as e:
        log(f"OCR failed: {e}")
        return ''


def _row_header_text(img):
    """OCR the row-header band — where the currently-focused row's title
    settles once vertical scrolling stops — to identify which row this is.
    """
    return _ocr(img.crop(HEADER_CROP)).strip()


def _tile_caption_text(img, column):
    """OCR the caption band under one tile column (0-indexed from the row's
    left edge). Every tile shows its own caption regardless of focus.
    """
    x0 = TILE_LEFT_X0 + column * TILE_PITCH
    return _ocr(img.crop((x0, CAPTION_Y0, x0 + TILE_CAPTION_WIDTH, CAPTION_Y1)))


def _wake_and_launch(ip):
    """Wake Fire TV and launch YouTube TV to its home screen (not a deep link)."""
    mac = FIRE_TV_MAC_ADDRESSES.get(ip)
    if mac:
        log(f"Sending WoL to {ip} ({mac})")
        try:
            _send_wol(mac)
        except Exception as e:
            log(f"WoL failed: {e}")
        time.sleep(1)

    if _wait_for_adb_ready(ip, max_wait_seconds=15):
        log("ADB confirmed ready")
    else:
        log("ADB not confirmed ready after 15s wait — proceeding anyway")

    _adb(ip, 'input keyevent KEYCODE_WAKEUP')
    time.sleep(2)

    log("Force-stopping YouTube TV")
    _adb(ip, f'am force-stop {YTV_PKG}')
    time.sleep(2)

    log("Launching YouTube TV")
    _adb(ip, f'am start -n {YTV_ACTIVITY}')
    log("Waiting 18s for YouTube TV to fully load...")
    time.sleep(18)


def _reset_to_ytv_home(ip):
    """Reset to YouTube TV home screen — known good starting point for retry."""
    log("Resetting to YouTube TV home...")
    _adb(ip, f'am force-stop {YTV_PKG}')
    time.sleep(2)
    _adb(ip, f'am start -n {YTV_ACTIVITY}')
    log("Waiting 15s for YouTube TV to reload...")
    time.sleep(15)


def _scroll_down_to_nfl_row(ip, max_downs=12):
    """Press DOWN repeatedly until the row header reads 'NFL'.

    Stuck detection (same header 3x in a row) means we hit the bottom of
    the page without finding it.
    """
    last_header = None
    stuck_count = 0

    for i in range(max_downs):
        img = _screenshot(ip)
        header = _row_header_text(img) if img else ''
        log(f"DOWN iteration {i}: row header = '{header}'")

        if header.strip().upper() == 'NFL':
            log("Found NFL row!")
            return True

        if header == last_header:
            stuck_count += 1
            if stuck_count >= 3:
                log("Stuck — reached bottom of page without finding NFL row")
                return False
        else:
            stuck_count = 0
            last_header = header

        _adb(ip, 'input keyevent KEYCODE_DPAD_DOWN')
        time.sleep(1.5)

    log(f"NFL row not found after {max_downs} DOWN presses")
    return False


def _reset_row_to_start(ip, presses=20):
    """Press LEFT repeatedly to guarantee focus is back at column 0 of the row."""
    log(f"Resetting row to start ({presses}x LEFT)")
    for _ in range(presses):
        _adb(ip, 'input keyevent KEYCODE_DPAD_LEFT')
        time.sleep(0.3)
    time.sleep(1)


def _extract_network(caption_text):
    """Extract the broadcast network from a row tile's caption, e.g.
    'NFL ST - CBS - 12:03 PM' -> 'CBS', 'FOX 4 -12:02 PM' -> 'FOX',
    'KCTV 5-12:04 PM' -> 'CBS' (KCTV 5 IS the KC CBS affiliate), 'KSHB
    7:15 PM' -> 'NBC' (KSHB is the KC NBC affiliate).

    Used only for the local-blackout fallback (see _is_blacked_out): when
    Sunday Ticket blacks out a game because it airs on the local station,
    this tells us which affiliate to direct-tune to via fire_tv.tune_channel
    without guessing between CBS and FOX.
    """
    first_line = caption_text.strip().split('\n')[0].upper()
    # Reverse of fire_tv.tune_channel's KC affiliate map -- these rows show
    # the literal local call sign already, so map it straight back to the
    # network name tune_channel expects.
    AFFILIATE_TO_NETWORK = {
        'KCTV 5': 'CBS', 'KCTV5': 'CBS',
        'FOX 4': 'FOX', 'FOX4': 'FOX',
        'KSHB': 'NBC',
        'KMBC': 'ABC',
    }
    for affiliate, network in AFFILIATE_TO_NETWORK.items():
        if affiliate in first_line:
            return network
    for network in ('CBS', 'FOX', 'NBC', 'ABC', 'ESPN'):
        if network in first_line:
            return network
    return None


def _scan_row_for_team(ip, target_team, max_batches=12):
    """Scan the NFL row for the target team.

    The row stays at a fixed vertical position throughout (only RIGHT/LEFT
    moves here). Every visible tile's caption is read each pass; if the
    target isn't visible, advance by one screen of columns and re-read.
    Once found, step RIGHT until it lands in column 0 (the row's fixed
    focus slot after a LEFT-reset), verifying by re-OCR after each move
    rather than trusting a blind keypress count.

    Returns (found, network): `found` is True if the target was located and
    selected; `network` (e.g. 'CBS') is the matched tile's broadcast network
    if one could be read, for the caller to fall back to a direct tune if
    this game turns out to be Sunday-Ticket-blacked-out.
    """
    last_seen = None
    stuck_count = 0
    total_advanced = 0

    for batch in range(max_batches):
        img = _screenshot(ip)
        if not img:
            time.sleep(2)
            continue

        captions = [(_tile_caption_text(img, col), col) for col in range(NUM_VISIBLE_COLUMNS)]
        summary = [c[:40].replace('\n', ' | ') for c, _ in captions]
        log(f"Batch {batch} (advanced {total_advanced}): {summary}")

        target_col = None
        target_text = None
        for text, col in captions:
            if _team_matches(target_team, text):
                target_col = col
                target_text = text
                break

        if target_col is not None:
            network = _extract_network(target_text)

            if target_col == 0:
                log(f"Target '{target_team}' is in focus column (0) — selecting")
                _adb(ip, 'input keyevent KEYCODE_DPAD_CENTER')
                time.sleep(3)
                return True, network

            log(f"Target '{target_team}' found at column {target_col} — moving RIGHT {target_col}")
            for _ in range(target_col):
                _adb(ip, 'input keyevent KEYCODE_DPAD_RIGHT')
                time.sleep(0.8)
            time.sleep(1.0)  # let focus/scroll animation fully settle before verifying

            verify_img = _screenshot(ip)
            verify_text = _tile_caption_text(verify_img, 0) if verify_img else ''
            if _team_matches(target_team, verify_text):
                log("VERIFY OK: target confirmed in focus column — selecting")
                _adb(ip, 'input keyevent KEYCODE_DPAD_CENTER')
                time.sleep(3)
                return True, network

            log(f"VERIFY FAILED: column 0 reads '{verify_text[:40]}' — retrying scan from here")
            continue

        current_key = str(summary)
        if current_key == last_seen:
            stuck_count += 1
            if stuck_count >= 3:
                log("Same tiles 3x — reached end of row")
                return False, None
        else:
            stuck_count = 0
            last_seen = current_key

        log(f"Target not in this batch, advancing RIGHT {NUM_VISIBLE_COLUMNS - 1}")
        for _ in range(NUM_VISIBLE_COLUMNS - 1):
            _adb(ip, 'input keyevent KEYCODE_DPAD_RIGHT')
            time.sleep(0.8)
        total_advanced += NUM_VISIBLE_COLUMNS - 1

    log(f"Target '{target_team}' not found after {max_batches} batches")
    return False, None


def _find_highlighted_button(img, region):
    """Find the bright/white pill-shaped highlighted control within `region`
    (x0,y0,x1,y1) and OCR just that tight crop.

    Focused controls in YouTube TV render as a solid light rounded-rect
    (dark text on a light pill) against the dark-background/light-text menu
    around them. OCR'ing the whole region in one pass mixes both color
    polarities and tesseract's binarization reliably drops the highlighted
    text entirely (confirmed live: a menu region containing a focused
    "Watch now" pill OCR'd as just "About / Upcoming / Suggested" — the
    highlighted item vanished). Isolating the bright bounding box first and
    OCR'ing only that fixes it.
    """
    crop = img.crop(region)
    arr = np.array(crop.convert('L'))
    bright = arr > 200
    rows = np.where(bright.any(axis=1))[0]
    cols = np.where(bright.any(axis=0))[0]
    if len(rows) == 0 or len(cols) == 0:
        return ''
    y0, y1 = int(rows.min()), int(rows.max())
    x0, x1 = int(cols.min()), int(cols.max())
    if (y1 - y0) < 15 or (x1 - x0) < 30:
        return ''
    tight = crop.crop((x0, y0, x1 + 1, y1 + 1))
    return _ocr(tight).strip()


def _check_media_playing(ip):
    """Check Android's media_session state for YouTube TV's player to confirm
    actual playback, and return its now-playing description for verification.

    A pixel/screenshot-based check (e.g. comparing two frames for motion)
    cannot work on this app: YouTube TV's video surface is DRM-protected, so
    `screencap` always returns solid black for it regardless of whether
    anything is actually playing — confirmed live (a real, actively-playing
    Bengals @ Buccaneers game screenshotted as pure black). `dumpsys
    media_session` reads the OS-level playback state directly, unaffected
    by DRM, and its metadata even names the two teams currently playing —
    enough to confirm not just that *something* is playing, but that it's
    the right game.

    Returns (is_playing, description).
    """
    output = _adb(ip, 'dumpsys media_session')
    if not output:
        return False, ''
    idx = output.find('starboard_media')  # YouTube TV's Cobalt/Starboard player session
    if idx == -1:
        return False, ''
    block = output[idx:idx + 1500]
    is_playing = 'PlaybackState {state=3' in block  # state=3 == Android's STATE_PLAYING
    desc_match = re.search(r'description=([^,]*),', block)
    description = desc_match.group(1).strip() if desc_match else ''
    return is_playing, description


def _select_watch_button(ip, target_team, max_attempts=5):
    """After selecting a game tile, find and press a Watch/Play-style control,
    then positively confirm playback actually started via _check_media_playing
    rather than assuming it from the absence of a menu.

    YouTube TV shows different post-select screens depending on game state:
    a pre-kickoff game shows a detail page with a left-side vertical menu
    ("Watch now" / About / Upcoming / Suggested); a live game instead pops
    a right-side "How would you like to begin watching?" panel ("Join live"
    / "Watch in multiview") — confirmed live against an actual kickoff.
    Both regions are checked each pass since either can appear. The
    highlighted control is isolated via _find_highlighted_button rather
    than OCR'd along with the rest of the screen — see its docstring; a
    whole-screen OCR here also fails for a different reason (mixes in
    unrelated row thumbnails/captions from elsewhere on the page).
    """
    # Deliberately excludes a bare 'watch' — "Watch in multiview" (a real
    # sibling option next to "Join live", always present as static menu
    # text on that panel regardless of what's focused) contains that
    # substring and would otherwise match, sending playback into multiview
    # instead of the single requested game.
    WATCH_WORDS = ['watch now', 'watch live', 'join live', 'play', 'resume', 'tune in']
    BLOCKED_WORDS = ['sunday ticket', 'subscribe', 'purchase', 'add channel']
    LEFT_MENU_REGION = (60, 380, 500, 900)
    RIGHT_PANEL_REGION = (1150, 170, 1920, 700)

    for attempt in range(max_attempts):
        time.sleep(2)
        img = _screenshot(ip)
        if not img:
            continue

        # Check both regions unconditionally and prefer whichever actually
        # contains a real watch-action match. Checking left-then-right only
        # "if left was empty" is unreliable: LEFT_MENU_REGION's y-range
        # overlaps the NFL row's own tile-caption band, so if CENTER hasn't
        # actually navigated anywhere yet (still sitting on the row), the
        # still-focused tile's caption reads as non-empty "highlighted"
        # text and permanently blocks ever checking the right panel where
        # "Join live" actually lives — confirmed live: this looped 5
        # attempts x3 retries reading the row's own caption the whole time.
        left_text = _find_highlighted_button(img, LEFT_MENU_REGION).lower()
        right_text = _find_highlighted_button(img, RIGHT_PANEL_REGION).lower()
        if any(w in left_text for w in WATCH_WORDS):
            highlighted = left_text
        elif any(w in right_text for w in WATCH_WORDS):
            highlighted = right_text
        else:
            highlighted = left_text or right_text
        log(f"Post-select attempt {attempt}: left='{left_text}' right='{right_text}'")

        if any(w in highlighted for w in WATCH_WORDS):
            log("Watch/Play control focused — pressing CENTER")
            _adb(ip, 'input keyevent KEYCODE_DPAD_CENTER')
            time.sleep(3)
            continue  # some flows need a second confirmation — loop back to re-check

        if _team_matches(target_team, highlighted):
            # We're still reading the NFL row's own focused-tile caption —
            # the earlier CENTER press on the tile never actually navigated
            # anywhere (confirmed live: this repeated unchanged for every
            # attempt until the retry gave up). Press CENTER again rather
            # than falling through to a motion check that can only fail.
            log("Still on the row (reading its own tile caption) — pressing CENTER again")
            _adb(ip, 'input keyevent KEYCODE_DPAD_CENTER')
            time.sleep(3)
            continue

        if _is_blacked_out(img):
            # Must be checked BEFORE trusting the media session: confirmed
            # live that YouTube TV's starboard_media session keeps reporting
            # state=3 (STATE_PLAYING) with the correct game metadata even
            # while the screen is showing this dead-end blackout message —
            # the underlying player pipeline reports itself active
            # regardless of whether the app is actually letting the video
            # through, so media-session state alone falsely confirmed
            # "success" here until this check was added.
            log("Blacked out (airing on local station) — cannot proceed automatically")
            return {'success': False, 'team': target_team, 'error': 'blacked_out'}

        full_text = _ocr(img).lower()
        if any(w in full_text for w in BLOCKED_WORDS):
            log("Hit a subscription/purchase screen — cannot proceed automatically")
            return {'success': False, 'team': target_team, 'error': 'subscription_required'}

        # No watch-style control focused any more -- either we're on live
        # video, or we've stalled on some other static screen (loading, an
        # error dialog, a not-yet-live game with nothing to play). Confirm
        # via the OS media session rather than the screen — see
        # _check_media_playing's docstring for why a pixel/frame check
        # can't work on this app's DRM-protected video surface.
        log("No watch/play control focused — checking media session for actual playback")
        is_playing, description = _check_media_playing(ip)
        log(f"Media session: playing={is_playing}, now-playing='{description}'")
        if is_playing:
            if description and not _team_matches(target_team, description):
                log(f"WARNING: playing, but description doesn't mention '{target_team}' — may be the wrong game")
            return {'success': True, 'team': target_team}

        log("Not playing yet — retrying")

    # One last check with a longer wait before giving up
    time.sleep(3)
    img = _screenshot(ip)
    if img and _is_blacked_out(img):
        log("Blacked out (airing on local station) on final check")
        return {'success': False, 'team': target_team, 'error': 'blacked_out'}

    is_playing, description = _check_media_playing(ip)
    if is_playing:
        log(f"Media session confirms playback on final check: '{description}'")
        return {'success': True, 'team': target_team}

    log("Could not confirm playback started — media session never reported playing")
    return {'success': False, 'team': target_team, 'error': 'playback_not_confirmed'}


def _is_blacked_out(img):
    """Detect NFL Sunday Ticket's local-blackout screen ('This game is
    airing on your local station.', shown with a crossed-out-eye icon) --
    confirmed live against a real Sunday Ticket blackout. Shown when the
    selected game is the one already airing on the viewer's local CBS/FOX
    affiliate, so Sunday Ticket won't play it and the local channel must
    be tuned directly instead (see _direct_tune_local_channel).
    """
    if not img:
        return False
    return 'airing on your local station' in _ocr(img).lower()


def _direct_tune_local_channel(ip, network):
    """Tune directly to the local CBS/FOX/NBC/ABC affiliate for a
    Sunday-Ticket-blacked-out game.

    Reuses fire_tv.tune_channel (via FireTVDevice) rather than
    reimplementing the KC-affiliate deep-link logic here, so the affiliate
    map stays a single source of truth shared with the rest of the app.
    """
    device = FireTVDevice(device_id=ip, device_name=ip, device_ip=ip)
    return asyncio.run(device.tune_channel(network))


def launch_game(ip, away_team, home_team, _run_id=None):
    """Launch an NFL game via YouTube TV's on-screen NFL row."""
    if _run_id is None:
        _run_id = start_run({
            'type': 'nfl_launcher',
            'ip': ip,
            'away_team': away_team,
            'home_team': home_team,
            'status': 'in_progress',
        })

    raw_target = away_team or home_team
    target_team = _normalize_team(raw_target)
    other_team = None
    if away_team and home_team:
        other_raw = home_team if raw_target == away_team else away_team
        other_team = _normalize_team(other_raw)
    log(f"Target team: '{raw_target}' -> normalized: '{target_team}'")

    result = None
    try:
        for attempt in range(3):
            if attempt > 0:
                log(f"=== RETRY {attempt} — resetting to YouTube TV home ===")
                _reset_to_ytv_home(ip)
            else:
                _wake_and_launch(ip)

            if not _scroll_down_to_nfl_row(ip):
                log("Could not find NFL row, will retry")
                continue

            _reset_row_to_start(ip)

            found, network = _scan_row_for_team(ip, target_team)
            if not found and other_team and other_team != target_team:
                log(f"'{target_team}' not found, trying '{other_team}'")
                _reset_row_to_start(ip)
                found, network = _scan_row_for_team(ip, other_team)
                if found:
                    target_team = other_team

            if not found:
                log("Team not found in NFL row, will retry")
                continue

            time.sleep(2)  # let the post-select screen settle before checking for blackout
            if _is_blacked_out(_screenshot(ip)):
                log(f"Blacked out on Sunday Ticket (airs on local station) — "
                    f"falling back to direct tune of '{network}'")
                if not network:
                    log("Could not determine the broadcast network from the row — will retry")
                    continue
                tune_result = _direct_tune_local_channel(ip, network)
                if tune_result.get('status') == 'success':
                    return {'success': True, 'team': target_team, 'method': 'direct_tune', 'channel': network}
                log(f"Direct tune fallback failed: {tune_result.get('message')}, will retry")
                continue

            result = _select_watch_button(ip, target_team)
            if result.get('success'):
                return result

            if result.get('error') == 'blacked_out':
                # Same blackout, just caught later (during the watch-button
                # step instead of immediately after selection) — same
                # direct-tune fallback, using the network already read off
                # the row tile at selection time.
                log(f"Blacked out (caught during watch-button step) — "
                    f"falling back to direct tune of '{network}'")
                if network:
                    tune_result = _direct_tune_local_channel(ip, network)
                    if tune_result.get('status') == 'success':
                        return {'success': True, 'team': target_team, 'method': 'direct_tune', 'channel': network}
                    log(f"Direct tune fallback failed: {tune_result.get('message')}, will retry")
                else:
                    log("Could not determine the broadcast network from the row — will retry")
                continue

            log(f"Watch step failed ({result.get('error')}), will retry")

        result = result or {'error': f'Could not find or launch {away_team} vs {home_team} after 3 attempts'}
        return result
    finally:
        if _run_id:
            log_step(
                'launch_game',
                {'ip': ip, 'away_team': away_team, 'home_team': home_team},
                result,
                status='success' if (result and result.get('success')) else 'failure',
                duration=0
            )
            from debug_logging.step_logger import get_run
            run_data = get_run(_run_id)
            steps = run_data.get('steps', []) if run_data else []
            run_metadata = {
                'type': 'nfl_launcher',
                'ip': ip,
                'away_team': away_team,
                'home_team': home_team,
                'status': 'success' if (result and result.get('success')) else 'failure',
                'result': result,
            }
            run_storage.save_run(_run_id, steps, metadata=run_metadata)


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print(json.dumps({'error': 'Usage: nfl_launcher.py <ip> <away_team> <home_team>'}))
        sys.exit(1)

    ip = sys.argv[1]
    away = sys.argv[2]
    home = sys.argv[3]

    try:
        result = launch_game(ip, away, home)
        print(json.dumps(result))
        sys.exit(0 if result.get('success') else 1)
    except Exception as e:
        print(json.dumps({'error': str(e)}))
        sys.exit(1)
