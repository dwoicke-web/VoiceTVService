"""
TV Control routes - Control TV devices and launch content
"""

import asyncio
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
        smartthings_token=os.environ.get('SMARTTHINGS_TOKEN')
    )
    manager.register_device(samsung_tv)

    # Create Fire TV devices (4 surrounding TVs)
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


@tv_control_bp.route('/launch', methods=['POST'])
def launch_content():
    """
    Launch content on a specific TV
    Request body:
        - tv_id: TV identifier
        - content_id: Content identifier
        - service: Streaming service name
    """
    data = request.get_json()

    tv_id = data.get('tv_id')
    content_id = data.get('content_id')
    service = data.get('service')

    if not all([tv_id, content_id, service]):
        return jsonify({'error': 'Missing required fields: tv_id, content_id, service'}), 400

    try:
        # Initialize TV devices
        manager = _initialize_tv_devices()

        # Get the TV device
        device = manager.get_device(tv_id)
        if not device:
            return jsonify({
                'error': f'TV device {tv_id} not found',
                'available_devices': list(manager.devices.keys())
            }), 404

        # Launch app asynchronously
        loop = _get_or_create_event_loop()
        result = loop.run_until_complete(device.launch_app(service, content_id))

        return jsonify({
            'status': 'success',
            'message': f'Launching {service} on {device.device_name}',
            'tv_id': tv_id,
            'tv_name': device.device_name,
            'content_id': content_id,
            'service': service,
            'device_info': {
                'device_type': device.device_type,
                'is_connected': device.is_connected
            }
        }), 200

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
