"""
Device Configuration Routes - Get device/TV information
"""

import os
import sys
from flask import Blueprint, jsonify

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
devices_bp = Blueprint('devices', __name__, url_prefix='/api')


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


@devices_bp.route('/tvs', methods=['GET'])
def get_tvs():
    """Get available TV devices for the UI"""
    try:
        manager = _initialize_tv_devices()

        tvs = []
        for device_id, device in manager.devices.items():
            # Only include primary TV displays (not Roku sources)
            if device_id in ['big_screen', 'upper_left', 'upper_right', 'lower_left', 'lower_right']:
                tv_info = {
                    'id': device_id,
                    'name': device.device_name,
                    'type': device.device_type,
                    'size': '75"' if device_id == 'big_screen' else '32"',
                    'position': device_id if device_id != 'big_screen' else 'center',
                    'is_connected': device.is_connected,
                }

                # Add size info
                if device_id == 'big_screen':
                    tv_info['specs'] = '75" Samsung Smart TV'
                else:
                    tv_info['specs'] = '32" Amazon Fire TV'

                tvs.append(tv_info)

        # Sort TVs: big_screen first, then corners (upper_left, lower_left, upper_right, lower_right)
        tv_order = ['big_screen', 'upper_left', 'lower_left', 'upper_right', 'lower_right']
        tvs_sorted = sorted(tvs, key=lambda x: tv_order.index(x['id']))

        return jsonify({
            'status': 'success',
            'tvs': tvs_sorted,
            'total': len(tvs_sorted)
        }), 200

    except Exception as e:
        logger.error(f"Error getting TVs: {e}")
        return jsonify({'error': str(e)}), 500


@devices_bp.route('/devices', methods=['GET'])
def get_all_devices():
    """Get all devices including content sources (Roku) and displays (Fire TV/Samsung)"""
    try:
        manager = _initialize_tv_devices()

        devices = []
        for device_id, device in manager.devices.items():
            device_info = {
                'id': device_id,
                'name': device.device_name,
                'type': device.device_type,
                'is_connected': device.is_connected,
            }

            # Add device-specific info
            if hasattr(device, 'broadcast_channel'):
                device_info['channel'] = device.broadcast_channel
            if hasattr(device, 'device_ip') and device.device_ip:
                device_info['ip'] = device.device_ip

            devices.append(device_info)

        return jsonify({
            'status': 'success',
            'devices': devices,
            'total': len(devices)
        }), 200

    except Exception as e:
        logger.error(f"Error getting devices: {e}")
        return jsonify({'error': str(e)}), 500


@devices_bp.route('/services', methods=['GET'])
def get_services():
    """Get list of supported streaming services"""
    services = [
        {
            'id': 'netflix',
            'name': 'Netflix',
            'icon': '📺',
            'available': True
        },
        {
            'id': 'prime_video',
            'name': 'Prime Video',
            'icon': '🎬',
            'available': True
        },
        {
            'id': 'youtube',
            'name': 'YouTube',
            'icon': '▶️',
            'available': True
        },
        {
            'id': 'youtube_tv',
            'name': 'YouTube TV',
            'icon': '📺',
            'available': True
        },
        {
            'id': 'hulu',
            'name': 'Hulu',
            'icon': '🎪',
            'available': True
        },
        {
            'id': 'hbo_max',
            'name': 'HBO Max',
            'icon': '👑',
            'available': True
        },
        {
            'id': 'espn_plus',
            'name': 'ESPN+',
            'icon': '⚽',
            'available': True
        },
        {
            'id': 'peacock',
            'name': 'Peacock',
            'icon': '🦚',
            'available': True
        },
        {
            'id': 'fandango',
            'name': 'Fandango',
            'icon': '🎟️',
            'available': True
        },
        {
            'id': 'vudu',
            'name': 'Vudu',
            'icon': '🎞️',
            'available': True
        },
    ]

    return jsonify({
        'status': 'success',
        'services': services,
        'total': len(services)
    }), 200
