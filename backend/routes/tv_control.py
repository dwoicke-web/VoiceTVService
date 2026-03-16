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
from apis.tv_control.roku import RokuDevice
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

        status_code = 200 if result.get('status') == 'success' else 500
        return jsonify(result), status_code

    except Exception as e:
        logger.error(f"Error resetting channel: {e}", exc_info=True)
        return jsonify({
            'error': 'Failed to reset channel',
            'message': str(e)
        }), 500
