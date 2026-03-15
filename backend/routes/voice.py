"""
Voice control routes - Handle voice commands and speech-to-text processing
"""

import asyncio
import sys
import os
import json
from flask import Blueprint, request, jsonify

# Ensure correct Python path for imports
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from apis.voice.speech_processor import get_speech_processor
from apis.voice.command_parser import get_command_parser
from apis.sonos import get_sonos_manager
from apis.tv_control import get_tv_manager
from apis.tv_control.smartthings import SamsungSmartThingsDevice
from apis.tv_control.fire_tv import FireTVDevice

voice_bp = Blueprint('voice', __name__, url_prefix='/api/voice')


def _initialize_tv_devices_for_voice():
    """Initialize TV devices for voice control"""
    manager = get_tv_manager()

    # Only initialize once
    if len(manager.devices) > 0:
        return manager

    # Create Samsung TV device
    samsung_tv = SamsungSmartThingsDevice(
        device_id='big_screen',
        device_name='Big Screen',
        smartthings_token=os.environ.get('SMARTTHINGS_TOKEN')
    )
    manager.register_device(samsung_tv)

    # Create Fire TV devices
    fire_tv_positions = [
        ('upper_left', 'Upper Left'),
        ('upper_right', 'Upper Right'),
        ('lower_left', 'Lower Left'),
        ('lower_right', 'Lower Right')
    ]

    for device_id, device_name in fire_tv_positions:
        fire_tv = FireTVDevice(
            device_id=device_id,
            device_name=device_name,
            device_ip=os.environ.get(f'FIRETV_{device_id.upper()}_IP')
        )
        manager.register_device(fire_tv)

    return manager


def _get_or_create_event_loop():
    """Get or create event loop for async operations"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("Event loop is closed")
        return loop
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


@voice_bp.route('/transcribe', methods=['POST'])
def transcribe_audio():
    """
    Transcribe audio to text
    Request body:
        - audio_file: Audio file (multipart/form-data) OR
        - audio_data: Base64 encoded audio data
    """
    try:
        processor = get_speech_processor()
        loop = _get_or_create_event_loop()

        # Handle file upload
        if 'audio_file' in request.files:
            audio_file = request.files['audio_file']
            # In real implementation, would save and transcribe
            # For now, use mock transcription
            result = loop.run_until_complete(processor.transcribe_audio('mock.wav'))
        else:
            # Handle raw audio data
            audio_data = request.get_json().get('audio_data')
            if not audio_data:
                return jsonify({'error': 'No audio data provided'}), 400

            result = loop.run_until_complete(processor.transcribe_stream(audio_data.encode()))

        return jsonify(result), 200

    except Exception as e:
        print(f"Error transcribing audio: {e}")
        return jsonify({
            'error': 'Transcription failed',
            'message': str(e)
        }), 500


@voice_bp.route('/command', methods=['POST'])
def process_voice_command():
    """
    Process a voice command
    Request body:
        - transcript: Transcribed text OR
        - audio_file: Audio file to transcribe and process
    """
    try:
        data = request.get_json() if request.is_json else {}
        transcript = data.get('transcript')

        # If transcript not provided, transcribe audio first
        if not transcript:
            processor = get_speech_processor()
            loop = _get_or_create_event_loop()

            if 'audio_file' in request.files:
                audio_file = request.files['audio_file']
                transcribe_result = loop.run_until_complete(processor.transcribe_audio('mock.wav'))
                transcript = transcribe_result.get('transcript')
            else:
                return jsonify({'error': 'Provide transcript or audio_file'}), 400

        if not transcript:
            return jsonify({'error': 'Could not transcribe audio'}), 400

        # Parse command
        parser = get_command_parser()
        command = parser.parse_command(transcript)

        return jsonify({
            'status': 'success',
            'transcript': transcript,
            'command': command
        }), 200

    except Exception as e:
        print(f"Error processing command: {e}")
        return jsonify({
            'error': 'Command processing failed',
            'message': str(e)
        }), 500


@voice_bp.route('/execute', methods=['POST'])
def execute_voice_command():
    """
    Execute a parsed voice command
    Request body:
        - transcript: Original voice command text
        - intent: Command intent (play_content, search, etc.)
        - content_name: Content to play (for play commands)
        - tv_id: Target TV (for play commands)
        - service: Streaming service (for play commands)
        - query: Search query (for search commands)
    """
    try:
        data = request.get_json()
        intent = data.get('intent')
        transcript = data.get('transcript', '')

        # Parse if only transcript provided
        if not intent and transcript:
            parser = get_command_parser()
            command = parser.parse_command(transcript)
            intent = command.get('intent')
            data.update(command)

        loop = _get_or_create_event_loop()
        result = {'status': 'error', 'message': 'Unknown intent'}

        if intent == 'play_content':
            result = _execute_play_command(data, loop)
        elif intent == 'search':
            result = _execute_search_command(data, loop)
        elif intent == 'control_volume':
            result = _execute_volume_command(data, loop)
        elif intent == 'control_power':
            result = _execute_power_command(data, loop)

        # Provide voice feedback
        sonos = get_sonos_manager()
        sonos_device = sonos.get_device('living_room_sonos')

        if sonos_device and result.get('status') == 'success':
            feedback_text = result.get('voice_response', f"Done. {result.get('message', '')}")
            loop.run_until_complete(sonos_device.speak(feedback_text))

        return jsonify(result), 200 if result.get('status') == 'success' else 400

    except Exception as e:
        print(f"Error executing command: {e}")
        return jsonify({
            'error': 'Command execution failed',
            'message': str(e)
        }), 500


def _execute_play_command(data: dict, loop) -> dict:
    """Execute a play content command"""
    content_name = data.get('content_name')
    tv_id = data.get('tv_id')
    service = data.get('service')

    if not content_name or not tv_id:
        return {
            'status': 'error',
            'message': 'Content name and TV required'
        }

    tv_manager = _initialize_tv_devices_for_voice()

    device = tv_manager.get_device(tv_id)
    if not device:
        return {
            'status': 'error',
            'message': f'TV {tv_id} not found'
        }

    # Use service if specified, otherwise search for content
    if service:
        result = loop.run_until_complete(device.launch_app(service, content_name))
    else:
        result = loop.run_until_complete(device.launch_app('YouTube TV', content_name))

    result['voice_response'] = f"Now playing {content_name} on {device.device_name}"
    return result


def _execute_search_command(data: dict, loop) -> dict:
    """Execute a search command"""
    query = data.get('query')

    if not query:
        return {
            'status': 'error',
            'message': 'Search query required'
        }

    # In real implementation, would call search API
    return {
        'status': 'success',
        'message': f'Searching for {query}',
        'voice_response': f'Searching for {query}'
    }


def _execute_volume_command(data: dict, loop) -> dict:
    """Execute a volume control command"""
    tv_id = data.get('tv_id')
    level = data.get('level')
    action = data.get('action')

    if not tv_id:
        return {
            'status': 'error',
            'message': 'TV ID required'
        }

    tv_manager = _initialize_tv_devices_for_voice()
    device = tv_manager.get_device(tv_id)

    if not device:
        return {
            'status': 'error',
            'message': f'TV {tv_id} not found'
        }

    if level is not None:
        result = loop.run_until_complete(device.set_volume(level))
        result['voice_response'] = f"Volume set to {level} percent"
    else:
        result = {
            'status': 'success',
            'message': f'Volume {action}'
        }
        result['voice_response'] = f"Volume turned {action}"

    return result


def _execute_power_command(data: dict, loop) -> dict:
    """Execute a power control command"""
    tv_id = data.get('tv_id')
    action = data.get('action')

    if not tv_id or not action:
        return {
            'status': 'error',
            'message': 'TV ID and action required'
        }

    tv_manager = _initialize_tv_devices_for_voice()
    device = tv_manager.get_device(tv_id)

    if not device:
        return {
            'status': 'error',
            'message': f'TV {tv_id} not found'
        }

    if action == 'on':
        result = loop.run_until_complete(device.power_on())
        result['voice_response'] = f"{device.device_name} is now on"
    else:
        result = loop.run_until_complete(device.power_off())
        result['voice_response'] = f"{device.device_name} is now off"

    return result


@voice_bp.route('/sonos/status', methods=['GET'])
def get_sonos_status():
    """Get status of Sonos speakers"""
    try:
        sonos = get_sonos_manager()
        devices = sonos.get_all_devices()

        statuses = {}
        loop = _get_or_create_event_loop()

        for device_id, device in devices.items():
            status = loop.run_until_complete(device.get_status())
            statuses[device_id] = status

        return jsonify({
            'status': 'success',
            'devices': statuses,
            'total_devices': len(statuses)
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@voice_bp.route('/sonos/speak', methods=['POST'])
def sonos_speak():
    """Make Sonos speaker speak text"""
    try:
        data = request.get_json()
        device_id = data.get('device_id', 'living_room_sonos')
        text = data.get('text')

        if not text:
            return jsonify({'error': 'Text required'}), 400

        sonos = get_sonos_manager()
        device = sonos.get_device(device_id)

        if not device:
            return jsonify({'error': f'Device {device_id} not found'}), 404

        loop = _get_or_create_event_loop()
        result = loop.run_until_complete(device.speak(text))

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
