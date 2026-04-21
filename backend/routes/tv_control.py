"""
TV Control routes - Control TV devices and launch content
"""

import asyncio
import json
import sys
import os
import logging
from flask import Blueprint, request, jsonify

# Ensure correct Python path for imports
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from apis.tv_control import get_tv_manager
from apis.tv_control.smartthings import SamsungSmartThingsDevice
from apis.tv_control.fire_tv import FireTVDevice
from apis.tv_control.roku import RokuDevice
from apis.tv_control.now_playing import set_now_playing, clear_now_playing, clear_all as clear_all_now_playing, get_now_playing
from logging_config import get_logger

logger = get_logger(__name__)
tv_control_bp = Blueprint('tv_control', __name__, url_prefix='/api/tv')


def _get_or_create_event_loop():
    """Get or create event loop for async operations in Flask threads"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("Event loop is closed")
        return loop
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


def _initialize_tv_devices():
    """Initialize TV devices on first call"""
    manager = get_tv_manager()

    # Only initialize once
    if len(manager.devices) > 0:
        return manager

    # Create Samsung TV device (center big screen)
    samsung_tv = SamsungSmartThingsDevice(
        device_id='big_screen',
        device_name='Big Screen',
        smartthings_token=os.environ.get('SMARTTHINGS_TOKEN'),
        smartthings_device_id=os.environ.get('SAMSUNG_SMARTTHINGS_DEVICE_ID')
    )
    manager.register_device(samsung_tv)

    # Create Roku devices (content sources) and Fire TV devices (display)
    # Roku broadcasts on antenna channels that Fire TVs tune to
    tv_positions = [
        ('upper_left', 'Upper Left'),
        ('upper_right', 'Upper Right'),
        ('lower_left', 'Lower Left'),
        ('lower_right', 'Lower Right')
    ]

    # Create Roku devices (content sources)
    for device_id, device_name in tv_positions:
        roku = RokuDevice(
            device_id=f'{device_id}_roku',
            device_name=f'{device_name} Roku',
            device_ip=os.environ.get(f'ROKU_{device_id.upper()}_IP'),
            channel=int(os.environ.get(f'ROKU_{device_id.upper()}_CHANNEL', 0))
        )
        manager.register_device(roku)

    # Create Fire TV devices (displays)
    for device_id, device_name in tv_positions:
        fire_tv = FireTVDevice(
            device_id=device_id,
            device_name=device_name,
            device_ip=os.environ.get(f'FIRETV_{device_id.upper()}_IP')
        )
        manager.register_device(fire_tv)

    return manager


@tv_control_bp.route('/launch', methods=['POST'])
def launch_content():
    """
    Launch content on a specific TV
    Request body:
        - tv_id: TV identifier (fire TV position: upper_left, upper_right, etc.)
        - content_id: Content identifier
        - service: Streaming service name

    Routes the content launch to the corresponding Roku device that broadcasts
    to the Fire TV's antenna channel
    """
    data = request.get_json()

    tv_id = data.get('tv_id')
    content_id = data.get('content_id')
    service = data.get('service')
    title = data.get('title')  # Optional: program title for searching

    if not all([tv_id, content_id, service]):
        return jsonify({'error': 'Missing required fields: tv_id, content_id, service'}), 400

    try:
        # Initialize TV devices
        manager = _initialize_tv_devices()

        # Get the Fire TV device (for reference)
        fire_tv = manager.get_device(tv_id)
        if not fire_tv:
            return jsonify({
                'error': f'TV device {tv_id} not found',
                'available_devices': list(manager.devices.keys())
            }), 404

        # Get the corresponding Roku device (content source)
        roku_id = f'{tv_id}_roku'
        roku_device = manager.get_device(roku_id)
        if not roku_device:
            return jsonify({
                'error': f'Roku device {roku_id} not found',
                'available_devices': list(manager.devices.keys())
            }), 404

        # Launch app on Roku device asynchronously
        # The Fire TV will automatically show the antenna broadcast from the Roku
        # on its assigned antenna channel (7, 8, 10, or 11 depending on TV position)
        loop = _get_or_create_event_loop()
        result = loop.run_until_complete(roku_device.launch_app(service, content_id, title=title))

        # Track what's now playing
        set_now_playing(tv_id, service, title or content_id)

        # Add Fire TV info to response
        result['tv_id'] = tv_id
        result['fire_tv_name'] = fire_tv.device_name
        result['roku_device_id'] = roku_id

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error launching content - tv_id: {tv_id}, service: {service}: {e}", exc_info=True)
        return jsonify({
            'error': 'Failed to launch content',
            'message': str(e)
        }), 500


@tv_control_bp.route('/power', methods=['POST'])
def control_power():
    """
    Control TV power
    Request body:
        - tv_id: TV identifier
        - action: 'on' or 'off'
    """
    data = request.get_json()

    tv_id = data.get('tv_id')
    action = data.get('action')

    if not tv_id or action not in ['on', 'off']:
        return jsonify({'error': 'Missing or invalid tv_id or action'}), 400

    try:
        manager = _initialize_tv_devices()
        device = manager.get_device(tv_id)

        if not device:
            return jsonify({'error': f'TV device {tv_id} not found'}), 404

        loop = _get_or_create_event_loop()
        if action == 'on':
            result = loop.run_until_complete(device.power_on())
        else:
            result = loop.run_until_complete(device.power_off())

        result['tv_id'] = tv_id
        result['tv_name'] = device.device_name
        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@tv_control_bp.route('/volume', methods=['POST'])
def control_volume():
    """
    Control TV volume
    Request body:
        - tv_id: TV identifier
        - level: 0-100
    """
    data = request.get_json()

    tv_id = data.get('tv_id')
    level = data.get('level')

    if not tv_id or level is None or not (0 <= level <= 100):
        return jsonify({'error': 'Invalid tv_id or volume level'}), 400

    try:
        manager = _initialize_tv_devices()
        device = manager.get_device(tv_id)

        if not device:
            return jsonify({'error': f'TV device {tv_id} not found'}), 404

        loop = _get_or_create_event_loop()
        result = loop.run_until_complete(device.set_volume(level))

        result['tv_id'] = tv_id
        result['tv_name'] = device.device_name
        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@tv_control_bp.route('/input', methods=['POST'])
def change_input():
    """
    Change TV input source
    Request body:
        - tv_id: TV identifier
        - input_source: Input source name
    """
    data = request.get_json()

    tv_id = data.get('tv_id')
    input_source = data.get('input_source')

    if not tv_id or not input_source:
        return jsonify({'error': 'Missing tv_id or input_source'}), 400

    try:
        manager = _initialize_tv_devices()
        device = manager.get_device(tv_id)

        if not device:
            return jsonify({'error': f'TV device {tv_id} not found'}), 404

        # Launch URL based on input source
        loop = _get_or_create_event_loop()
        result = loop.run_until_complete(device.launch_url(input_source))

        result['tv_id'] = tv_id
        result['tv_name'] = device.device_name
        result['input_source'] = input_source
        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@tv_control_bp.route('/status/<tv_id>', methods=['GET'])
def get_tv_status(tv_id):
    """Get status of a specific TV"""
    try:
        manager = _initialize_tv_devices()
        device = manager.get_device(tv_id)

        if not device:
            return jsonify({'error': f'TV device {tv_id} not found'}), 404

        loop = _get_or_create_event_loop()
        result = loop.run_until_complete(device.get_status())

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@tv_control_bp.route('/status', methods=['GET'])
def get_all_tv_status():
    """Get status of all TVs"""
    try:
        manager = _initialize_tv_devices()
        statuses = {}

        loop = _get_or_create_event_loop()
        for device_id, device in manager.devices.items():
            status = loop.run_until_complete(device.get_status())
            statuses[device_id] = status

        return jsonify({
            'status': 'success',
            'devices': statuses,
            'total_devices': len(statuses)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@tv_control_bp.route('/power-all', methods=['POST'])
def power_all():
    """Power on or off all Fire TV devices"""
    try:
        data = request.get_json()
        action = data.get('action')  # 'on' or 'off'

        if action not in ['on', 'off']:
            return jsonify({'error': 'Action must be "on" or "off"'}), 400

        manager = _initialize_tv_devices()
        loop = _get_or_create_event_loop()
        results = {}

        # Find all Fire TV devices (excluding Samsung TV and other non-Fire TV devices)
        fire_tv_devices = [
            (device_id, device) for device_id, device in manager.devices.items()
            if isinstance(device, FireTVDevice)
        ]

        if not fire_tv_devices:
            return jsonify({'error': 'No Fire TV devices found'}), 404

        logger.info(f"Found {len(fire_tv_devices)} Fire TV devices: {[d[0] for d in fire_tv_devices]}")

        # Power on/off all Fire TVs simultaneously using asyncio.gather
        async def power_all_parallel():
            async def power_one(device_id, device):
                try:
                    if action == 'on':
                        coro = device.power_on()
                    else:
                        coro = device.power_off()
                    return device_id, await asyncio.wait_for(coro, timeout=30.0)
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout powering {action} {device_id}")
                    return device_id, {
                        'status': 'timeout',
                        'message': f'Fire TV {device_id} not responding - Enable ADB debugging',
                        'device_id': device_id
                    }
                except Exception as e:
                    logger.error(f"Error powering {action} {device_id}: {e}")
                    return device_id, {
                        'status': 'error',
                        'message': str(e),
                        'device_id': device_id
                    }

            tasks = [power_one(did, dev) for did, dev in fire_tv_devices]
            return await asyncio.gather(*tasks)

        parallel_results = loop.run_until_complete(power_all_parallel())
        for device_id, result in parallel_results:
            results[device_id] = result

        # Count successes
        successful = sum(1 for r in results.values() if r.get('status') == 'success')

        # Clear now-playing state on power off
        if action == 'off' and successful > 0:
            clear_all_now_playing()

        return jsonify({
            'status': 'success' if successful > 0 else 'partial',
            'action': action,
            'devices_affected': successful,
            'total_devices': len(fire_tv_devices),
            'results': results
        }), 200

    except Exception as e:
        logger.error(f"Error with power all command: {e}", exc_info=True)
        return jsonify({
            'error': 'Failed to execute power command',
            'message': str(e)
        }), 500


@tv_control_bp.route('/tune', methods=['POST'])
def tune_channel():
    """
    Tune to a YouTube TV channel on a specific Fire TV.

    Request body:
        - tv_id: TV identifier (upper_left, upper_right, lower_left, lower_right)
        - channel: Channel name (e.g., 'ESPN', 'Fox News', 'CNN')

    Launches YouTube TV (Cobalt) on the Fire TV via ADB deep link:
      1. `am force-stop com.amazon.firetv.youtube.tv`
      2. `am start -a VIEW -d https://tv.youtube.com/watch/<videoId> -n <pkg>/dev.cobalt.app.MainActivity`

    The previous Roku-ECP path (POST /launch/195316?contentId=...) was abandoned
    after the 2026-04-14 YouTube TV Roku app update made deep linking a no-op.
    Roku tune_channel still exists in roku.py for the Big Screen / future revert.
    """
    data = request.get_json()

    tv_id = data.get('tv_id')
    channel = data.get('channel')

    if not tv_id or not channel:
        return jsonify({'error': 'Missing required fields: tv_id, channel'}), 400

    try:
        manager = _initialize_tv_devices()

        # Get the Fire TV device for this position
        fire_tv = manager.get_device(tv_id)
        if not fire_tv:
            return jsonify({
                'error': f'Fire TV device {tv_id} not found',
                'available_devices': list(manager.devices.keys())
            }), 404

        # Run tune_channel in background thread so API responds immediately
        import threading
        def _bg_tune():
            try:
                bg_loop = asyncio.new_event_loop()
                bg_loop.run_until_complete(fire_tv.tune_channel(channel))
                bg_loop.close()
            except Exception as e:
                logger.error(f"Background tune_channel error: {e}")

        thread = threading.Thread(target=_bg_tune, daemon=True)
        thread.start()

        # Track what's now playing
        set_now_playing(tv_id, 'YouTubeTV', channel, channel=channel)

        return jsonify({
            'status': 'success',
            'message': f'Tuning to {channel} on {fire_tv.device_name}',
            'tv_id': tv_id,
            'channel': channel,
            'note': 'Channel tuning started in background'
        }), 200

    except Exception as e:
        logger.error(f"Error tuning channel - tv_id: {tv_id}, channel: {channel}: {e}", exc_info=True)
        return jsonify({
            'error': 'Failed to tune channel',
            'message': str(e)
        }), 500


@tv_control_bp.route('/launch-mlb', methods=['POST'])
def launch_mlb_game():
    """Launch the MLB app on a Fire TV and navigate to a specific game.

    Uses screen-scrape navigation:
      1. Force-stop and relaunch the MLB app
      2. Wait for full load, then dump the UI via uiautomator
      3. Parse team positions to find the target game card
      4. Navigate DOWN to games row, RIGHT x N to the card, SELECT

    If mlb_game_pk is provided, also attempts deep-link first (for regular
    season games with MLB.TV streams).

    Request body:
        - tv_id: TV identifier (upper_left, upper_right, lower_left, lower_right)
        - away_team: Away team short name (e.g., 'Yankees')
        - home_team: Home team short name (e.g., 'Cubs')
        - mlb_game_pk: Optional gamePk for deep-link attempt
        - title: Optional game title for logging
    """
    data = request.get_json()
    tv_id = data.get('tv_id')
    away_team = data.get('away_team', '')
    home_team = data.get('home_team', '')
    game_pk = data.get('mlb_game_pk')
    title = data.get('title', 'MLB game')

    if not tv_id:
        return jsonify({'error': 'Missing required field: tv_id'}), 400

    if not away_team and not home_team:
        return jsonify({'error': 'Missing required field: away_team or home_team'}), 400

    # Fire TV IP lookup
    FIRE_TV_IPS = {
        'upper_left': '192.168.4.80',
        'upper_right': '192.168.4.78',
        'lower_left': '192.168.4.93',
        'lower_right': '192.168.4.108',
    }
    fire_tv_ip = FIRE_TV_IPS.get(tv_id)
    if not fire_tv_ip:
        return jsonify({'error': f'No Fire TV IP configured for {tv_id}'}), 404

    try:
        import subprocess

        # Launch as separate subprocess — each TV gets its own process and ADB connection
        launcher_script = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'apis', 'tv_control', 'mlb_launcher.py'
        )
        python_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'venv', 'bin', 'python3'
        )

        cmd = [python_path, launcher_script, fire_tv_ip, away_team, home_team]
        log_file = f'/tmp/mlb_launch_{tv_id}.log'
        logger.info(f"MLB launching subprocess for {tv_id}: {' '.join(cmd)} > {log_file}")
        with open(log_file, 'w') as lf:
            subprocess.Popen(cmd, stdout=lf, stderr=lf)

        # Track what's now playing
        set_now_playing(tv_id, 'MLB', title)

        return jsonify({
            'status': 'success',
            'message': f'Launching {title} on {tv_id}',
            'tv_id': tv_id,
            'title': title,
            'method': 'screen-scrape',
            'note': 'MLB app launching — navigating to game automatically'
        }), 200

    except Exception as e:
        logger.error(f"Error launching MLB: {e}", exc_info=True)
        return jsonify({'error': 'Failed to launch MLB', 'message': str(e)}), 500


@tv_control_bp.route('/launch-espn', methods=['POST'])
def launch_espn_game():
    """Launch the ESPN app on a Fire TV and navigate to a specific game.

    Uses screen-scrape navigation directly on Fire TV (no Roku):
      1. Launch ESPN app on Fire TV via ADB
      2. Scroll DOWN to find the NHL row
      3. Scroll RIGHT through games, screen-scraping each position
      4. Select the matching game

    Request body:
        - tv_id: TV identifier (upper_left, upper_right, lower_left, lower_right)
        - away_team: Away team short name (e.g., 'Penguins')
        - home_team: Home team short name (e.g., 'Rangers')
        - title: Optional game title for logging
    """
    data = request.get_json()
    tv_id = data.get('tv_id')
    away_team = data.get('away_team', '')
    home_team = data.get('home_team', '')
    title = data.get('title', 'ESPN+ game')

    if not tv_id:
        return jsonify({'error': 'Missing required field: tv_id'}), 400

    if not away_team and not home_team:
        return jsonify({'error': 'Missing required field: away_team or home_team'}), 400

    # Fire TV IP lookup
    FIRE_TV_IPS = {
        'upper_left': '192.168.4.80',
        'upper_right': '192.168.4.78',
        'lower_left': '192.168.4.93',
        'lower_right': '192.168.4.108',
    }
    fire_tv_ip = FIRE_TV_IPS.get(tv_id)
    if not fire_tv_ip:
        return jsonify({'error': f'No Fire TV IP configured for {tv_id}'}), 404

    try:
        import subprocess

        # Launch as separate subprocess — each TV gets its own process and ADB connection
        launcher_script = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'apis', 'tv_control', 'espn_launcher.py'
        )
        python_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'venv', 'bin', 'python3'
        )

        cmd = [python_path, launcher_script, fire_tv_ip, away_team, home_team]

        log_file = f'/tmp/espn_launch_{tv_id}.log'
        logger.info(f"ESPN launching subprocess for {tv_id}: {' '.join(cmd)} > {log_file}")
        with open(log_file, 'w') as lf:
            subprocess.Popen(cmd, stdout=lf, stderr=lf)

        # Track what's now playing
        set_now_playing(tv_id, 'ESPN+', title)

        return jsonify({
            'status': 'success',
            'message': f'Launching {title} on {tv_id}',
            'tv_id': tv_id,
            'title': title,
            'method': 'screen-scrape',
            'note': 'ESPN app launching — navigating to game automatically'
        }), 200

    except Exception as e:
        logger.error(f"Error launching ESPN: {e}", exc_info=True)
        return jsonify({'error': 'Failed to launch ESPN', 'message': str(e)}), 500


@tv_control_bp.route('/cancel-operations', methods=['POST'])
def cancel_operations():
    """Kill all running ESPN and MLB launcher subprocesses."""
    import subprocess
    try:
        # Find and kill espn_launcher.py and mlb_launcher.py processes
        result = subprocess.run(
            ['pkill', '-f', 'espn_launcher.py|mlb_launcher.py'],
            capture_output=True, text=True
        )
        killed = result.returncode == 0

        # Also kill any lingering uiautomator processes on Fire TVs
        FIRE_TV_IPS = {
            'upper_left': '192.168.4.80',
            'upper_right': '192.168.4.78',
            'lower_left': '192.168.4.93',
            'lower_right': '192.168.4.108',
        }
        for name, ip in FIRE_TV_IPS.items():
            try:
                _run_cmd = f"kill $(pgrep -f 'adb.*{ip}')"
                subprocess.run(['bash', '-c', _run_cmd], capture_output=True, timeout=5)
            except Exception:
                pass

        return jsonify({
            'status': 'success',
            'message': 'All launcher operations cancelled' if killed else 'No operations were running',
            'killed': killed
        }), 200

    except Exception as e:
        logger.error(f"Error cancelling operations: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@tv_control_bp.route('/now-playing', methods=['GET'])
def now_playing():
    """Get what's currently playing on all TVs."""
    return jsonify(get_now_playing()), 200


@tv_control_bp.route('/reset-channel', methods=['POST'])
def reset_channel():
    """Reset Fire TV to antenna input and tune to specified channel"""
    try:
        data = request.get_json()
        device_id = data.get('device_id') or data.get('tv_id')  # Support both parameter names
        channel = data.get('channel')

        if not device_id:
            return jsonify({'error': 'Device ID is required'}), 400

        if channel is None:
            return jsonify({'error': 'Channel is required'}), 400

        try:
            channel = int(channel)
        except (ValueError, TypeError):
            return jsonify({'error': 'Channel must be a valid number'}), 400

        manager = _initialize_tv_devices()

        # Find the Fire TV device by ID
        fire_tv = manager.devices.get(device_id)

        if not fire_tv:
            return jsonify({'error': f'Device {device_id} not found'}), 404

        if not hasattr(fire_tv, 'reset_channel'):
            return jsonify({'error': f'{fire_tv.device_name} does not support channel reset'}), 400

        # Reset channel with timeout protection (10 seconds for ADB operations)
        loop = _get_or_create_event_loop()
        try:
            future = asyncio.ensure_future(fire_tv.reset_channel(channel))
            result = loop.run_until_complete(asyncio.wait_for(future, timeout=60.0))
        except asyncio.TimeoutError:
            logger.warning(f"Timeout resetting channel on {fire_tv.device_name}")
            result = {
                'status': 'timeout',
                'message': f'Fire TV {device_id} not responding - Enable ADB debugging (Settings > Developer Options > Enable ADB)',
                'device_id': device_id
            }
            future.cancel()

        # Clear now-playing on reset (back to antenna)
        clear_now_playing(device_id)

        status_code = 200 if result.get('status') == 'success' else 500
        return jsonify(result), status_code

    except Exception as e:
        logger.error(f"Error resetting channel: {e}", exc_info=True)
        return jsonify({
            'error': 'Failed to reset channel',
            'message': str(e)
        }), 500


# --- YouTube TV Channel Mappings ---

@tv_control_bp.route('/ytv-channels', methods=['GET'])
def get_ytv_channels():
    """Get all YouTube TV channel→videoId mappings"""
    from apis.tv_control.ytv_channels import get_mapper
    mapper = get_mapper()
    return jsonify(mapper.get_all_mappings()), 200


@tv_control_bp.route('/ytv-channels/upload', methods=['POST'])
def upload_ytv_browse_json():
    """Upload browse.json from YouTube TV DevTools to refresh channel mappings.

    Accepts either:
      - JSON body (the browse.json content directly)
      - Form file upload with field name 'file'
    """
    from apis.tv_control.ytv_channels import get_mapper
    mapper = get_mapper()

    try:
        # Try JSON body first
        if request.is_json:
            browse_data = request.get_json()
        elif 'file' in request.files:
            file = request.files['file']
            browse_data = json.loads(file.read().decode('utf-8'))
        else:
            return jsonify({'error': 'Send browse.json as JSON body or file upload'}), 400

        count = mapper.parse_browse_json(browse_data)

        if count == 0:
            return jsonify({
                'status': 'error',
                'message': 'No channels found in browse.json. Make sure you copied the full response from the browse API call in DevTools.'
            }), 400

        return jsonify({
            'status': 'success',
            'message': f'Extracted {count} channel mappings',
            'count': count,
            'updated_at': mapper.updated_at,
            'channels': mapper.mappings
        }), 200

    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON'}), 400
    except Exception as e:
        logger.error(f"Error processing browse.json upload: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@tv_control_bp.route('/ytv-channels/test/<channel_name>', methods=['POST'])
def test_ytv_deep_link(channel_name):
    """Test deep linking to a YouTube TV channel on a specific Roku.

    Query params:
      - tv_id: TV position (upper_left, upper_right, etc.)
    """
    from apis.tv_control.ytv_channels import get_mapper
    mapper = get_mapper()

    tv_id = request.args.get('tv_id', 'upper_right')
    video_id = mapper.get_video_id(channel_name)

    if not video_id:
        return jsonify({
            'status': 'error',
            'message': f'No videoId mapping for "{channel_name}". Upload browse.json first.',
            'available_channels': list(mapper.mappings.keys())
        }), 404

    try:
        manager = _initialize_tv_devices()
        roku_id = f'{tv_id}_roku'
        roku_device = manager.get_device(roku_id)

        if not roku_device:
            return jsonify({'error': f'Roku device {roku_id} not found'}), 404

        loop = _get_or_create_event_loop()
        success = loop.run_until_complete(
            roku_device.roku_client.launch_app('195316', params={'contentId': video_id, 'mediaType': 'live'})
        )

        return jsonify({
            'status': 'success' if success else 'error',
            'channel': channel_name,
            'video_id': video_id,
            'tv_id': tv_id,
            'message': f'Deep linked {channel_name} on {tv_id}' if success else 'Launch failed'
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
