"""
Voice control routes - Handle voice commands via Web Speech API transcripts
Executes commands on Fire TVs and Roku devices, provides Sonos TTS feedback
"""

import asyncio
import os
import logging
from flask import Blueprint, request, jsonify
from apis.voice.command_parser import get_command_parser
from apis.sonos import get_sonos_manager
from apis.tv_control.fire_tv import FireTVDevice
from apis.tv_control.roku import RokuDevice

logger = logging.getLogger(__name__)
voice_bp = Blueprint('voice', __name__, url_prefix='/api/voice')

# Fire TV device configs
FIRE_TVS = {
    'upper_left': {'name': 'Upper Left', 'ip': '192.168.4.80', 'channel': 7},
    'upper_right': {'name': 'Upper Right', 'ip': '192.168.4.78', 'channel': 10},
    'lower_left': {'name': 'Lower Left', 'ip': '192.168.4.93', 'channel': 8},
    'lower_right': {'name': 'Lower Right', 'ip': '192.168.4.108', 'channel': 11},
}


def _get_or_create_event_loop():
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError
        return loop
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


def _get_fire_tv(tv_id: str) -> FireTVDevice:
    """Get a Fire TV device by ID"""
    config = FIRE_TVS.get(tv_id)
    if not config:
        return None
    return FireTVDevice(
        device_id=tv_id,
        device_name=config['name'],
        device_ip=config['ip']
    )


def _get_roku(tv_id: str) -> RokuDevice:
    """Get a Roku device by TV ID"""
    roku_ip = os.environ.get(f'ROKU_{tv_id.upper()}_IP')
    if not roku_ip:
        return None
    config = FIRE_TVS.get(tv_id, {})
    return RokuDevice(
        device_id=f'{tv_id}_roku',
        device_name=f'{config.get("name", tv_id)} Roku',
        device_ip=roku_ip,
        channel=config.get('channel', 0)
    )


@voice_bp.route('/command', methods=['POST'])
def process_voice_command():
    """
    Process a voice command from the web UI.
    Expects JSON: { "transcript": "turn on all the TVs" }
    Parses the command, executes it, and returns the result.
    Optionally speaks feedback on Sonos.
    """
    try:
        data = request.get_json()
        transcript = data.get('transcript', '').strip()

        if not transcript:
            return jsonify({'error': 'No transcript provided'}), 400

        # Parse command
        parser = get_command_parser()
        command = parser.parse_command(transcript)
        intent = command.get('intent')

        logger.info(f"Voice command: '{transcript}' -> intent={intent}, command={command}")

        loop = _get_or_create_event_loop()
        result = {'status': 'error', 'message': 'Unknown command'}

        if intent == 'control_power':
            result = _execute_power(command, loop)
        elif intent == 'reset_antenna':
            result = _execute_reset_antenna(command, loop)
        elif intent == 'tune_channel':
            result = _execute_tune_channel(command, loop)
        elif intent == 'launch_app':
            result = _execute_launch_app(command, loop)
        elif intent == 'play_content':
            result = _execute_play(command, loop)
        elif intent == 'search':
            result = _execute_search(command, loop)
        elif intent == 'control_volume':
            result = command  # Volume handled client-side or mock
            result['status'] = 'success'

        # Add voice response
        voice_response = result.get('voice_response', command.get('voice_response', ''))
        result['voice_response'] = voice_response
        result['transcript'] = transcript
        result['parsed_intent'] = intent

        # Speak feedback on Sonos (non-blocking)
        speak_feedback = data.get('speak_feedback', True)
        if speak_feedback and voice_response:
            try:
                sonos = get_sonos_manager()
                loop.run_until_complete(sonos.speak(voice_response, volume=35))
            except Exception as e:
                logger.warning(f"Sonos TTS failed: {e}")

        return jsonify(result), 200 if result.get('status') == 'success' else 400

    except Exception as e:
        logger.error(f"Voice command error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


def _execute_power(command: dict, loop) -> dict:
    """Execute power on/off command"""
    action = command.get('action', 'on')
    tv_id = command.get('tv_id')

    if tv_id == 'all':
        # Power all Fire TVs in parallel
        async def power_all():
            tasks = []
            for tid in FIRE_TVS:
                device = _get_fire_tv(tid)
                if device:
                    if action == 'on':
                        tasks.append(asyncio.wait_for(device.power_on(), timeout=30))
                    else:
                        tasks.append(asyncio.wait_for(device.power_off(), timeout=30))
            return await asyncio.gather(*tasks, return_exceptions=True)

        results = loop.run_until_complete(power_all())
        successes = sum(1 for r in results if isinstance(r, dict) and r.get('status') == 'success')
        return {
            'status': 'success',
            'message': f'{successes}/4 TVs powered {action}',
            'devices_affected': successes,
            'voice_response': f"All TVs are now {'on' if action == 'on' else 'off'}"
        }
    elif tv_id:
        device = _get_fire_tv(tv_id)
        if not device:
            return {'status': 'error', 'message': f'TV {tv_id} not found'}
        if action == 'on':
            result = loop.run_until_complete(device.power_on())
        else:
            result = loop.run_until_complete(device.power_off())
        result['voice_response'] = f"{device.device_name} is now {action}"
        return result
    else:
        return {'status': 'error', 'message': 'Which TV? Say "all" or a specific TV name'}


def _execute_reset_antenna(command: dict, loop) -> dict:
    """Execute reset to antenna input"""
    tv_id = command.get('tv_id')

    if tv_id == 'all' or not tv_id:
        # Reset all
        async def reset_all():
            tasks = []
            for tid, config in FIRE_TVS.items():
                device = _get_fire_tv(tid)
                if device:
                    tasks.append(asyncio.wait_for(
                        device.reset_channel(config['channel']), timeout=30
                    ))
            return await asyncio.gather(*tasks, return_exceptions=True)

        results = loop.run_until_complete(reset_all())
        successes = sum(1 for r in results if isinstance(r, dict) and r.get('status') == 'success')
        return {
            'status': 'success',
            'message': f'{successes}/4 TVs reset to antenna',
            'voice_response': 'All TVs reset to antenna'
        }
    else:
        device = _get_fire_tv(tv_id)
        config = FIRE_TVS.get(tv_id, {})
        if not device:
            return {'status': 'error', 'message': f'TV {tv_id} not found'}
        result = loop.run_until_complete(device.reset_channel(config.get('channel', 0)))
        result['voice_response'] = f"{device.device_name} reset to antenna"
        return result


def _execute_tune_channel(command: dict, loop) -> dict:
    """Tune to a channel on YouTube TV via Roku"""
    channel = command.get('channel')
    tv_id = command.get('tv_id')

    if not channel:
        return {'status': 'error', 'message': 'Which channel?', 'voice_response': 'Which channel should I tune to?'}

    # If no TV specified, use upper_left as default
    if not tv_id:
        tv_id = 'upper_left'

    roku = _get_roku(tv_id)
    if roku:
        result = loop.run_until_complete(roku.tune_channel(channel))
        result['voice_response'] = f"Tuning to {channel} on {FIRE_TVS.get(tv_id, {}).get('name', tv_id)}"
        return result
    else:
        return {
            'status': 'error',
            'message': f'No Roku configured for {tv_id}',
            'voice_response': f"Cannot find Roku for {tv_id.replace('_', ' ')}"
        }


def _execute_launch_app(command: dict, loop) -> dict:
    """Launch a streaming app on a Roku device"""
    service = command.get('service')
    tv_id = command.get('tv_id')

    if not service:
        return {'status': 'error', 'message': 'Which app?'}

    # If no TV specified, use upper_left as default
    if not tv_id:
        tv_id = 'upper_left'

    roku = _get_roku(tv_id)
    if roku:
        result = loop.run_until_complete(roku.launch_app(service))
        result['voice_response'] = f"Launching {service} on {FIRE_TVS.get(tv_id, {}).get('name', tv_id)}"
        return result
    else:
        return {
            'status': 'error',
            'message': f'No Roku configured for {tv_id}',
            'voice_response': f"Cannot find Roku for {tv_id.replace('_', ' ')}"
        }


def _execute_play(command: dict, loop) -> dict:
    """Execute play content - routes to MLB app for baseball teams, Roku search for generic content"""
    content_name = command.get('content_name')
    tv_id = command.get('tv_id')
    service = command.get('service')
    mlb_team = command.get('mlb_team')

    if not content_name:
        return {'status': 'error', 'message': 'What should I play?'}
    if not tv_id:
        tv_id = 'upper_left'

    roku = _get_roku(tv_id)
    if not roku:
        return {'status': 'error', 'message': f'No Roku for {tv_id}'}

    tv_name = FIRE_TVS.get(tv_id, {}).get('name', tv_id)

    # MLB team detected → launch MLB app directly
    if service == 'MLB' or mlb_team:
        result = loop.run_until_complete(roku.launch_app('MLB'))
        result['voice_response'] = f"Opening MLB for {mlb_team or content_name} on {tv_name}"
        return result

    # Known streaming service → launch that app
    if service:
        result = loop.run_until_complete(roku.launch_app(service, content_id=content_name, title=content_name))
        result['voice_response'] = f"Playing {content_name} on {tv_name}"
        return result

    # Generic content → use Roku search/browse to find it
    result = loop.run_until_complete(roku.search_content(content_name))
    result['voice_response'] = f"Searching for {content_name} on {tv_name}"
    return result


def _execute_search(command: dict, loop) -> dict:
    """Execute a content search"""
    query = command.get('query')
    if not query:
        return {'status': 'error', 'message': 'What should I search for?'}

    # Use the search aggregator
    from apis.search import get_search_aggregator
    aggregator = get_search_aggregator()
    results = loop.run_until_complete(aggregator.search(query))

    total = results.get('total', 0)
    top_results = results.get('results', [])[:3]
    titles = [r.get('title', '') for r in top_results]

    voice = f"Found {total} results for {query}."
    if titles:
        voice += f" Top result: {titles[0]}."

    return {
        'status': 'success',
        'message': f'Found {total} results',
        'total': total,
        'top_results': top_results,
        'voice_response': voice
    }


@voice_bp.route('/sonos/status', methods=['GET'])
def get_sonos_status():
    """Get status of all Sonos speakers"""
    try:
        sonos = get_sonos_manager()
        loop = _get_or_create_event_loop()
        statuses = {}
        for device_id, device in sonos.get_all_devices().items():
            statuses[device_id] = loop.run_until_complete(device.get_status())
        return jsonify({'status': 'success', 'devices': statuses}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@voice_bp.route('/sonos/speak', methods=['POST'])
def sonos_speak():
    """Make Sonos Beam speak text"""
    try:
        data = request.get_json()
        text = data.get('text')
        if not text:
            return jsonify({'error': 'Text required'}), 400

        sonos = get_sonos_manager()
        loop = _get_or_create_event_loop()
        result = loop.run_until_complete(sonos.speak(text))
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@voice_bp.route('/test', methods=['GET'])
def test_voice():
    """Test voice command parsing"""
    test_commands = [
        "turn on all the TVs",
        "power off everything",
        "reset antenna on upper left",
        "launch Netflix on lower right",
        "play Breaking Bad on upper left",
        "search for Lakers",
        "open ESPN on upper right",
    ]
    parser = get_command_parser()
    results = []
    for cmd in test_commands:
        parsed = parser.parse_command(cmd)
        results.append({'input': cmd, 'parsed': parsed})
    return jsonify({'tests': results}), 200
