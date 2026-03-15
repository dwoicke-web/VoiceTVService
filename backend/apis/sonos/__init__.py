"""
Sonos speaker integration module
For discovering and controlling Sonos speakers for voice input/output
"""

import os
from typing import Dict, List, Optional, Any


class SonosDevice:
    """Represents a Sonos speaker device"""

    def __init__(self, device_id: str, device_name: str, ip_address: Optional[str] = None):
        """
        Initialize Sonos device

        Args:
            device_id: Unique device identifier
            device_name: Human-readable name
            ip_address: IP address of Sonos device
        """
        self.device_id = device_id
        self.device_name = device_name
        self.ip_address = ip_address
        self.is_connected = False
        self.volume = 50
        self.is_playing = False

    async def speak(self, text: str) -> Dict[str, Any]:
        """
        Play text-to-speech on the speaker

        Args:
            text: Text to speak

        Returns:
            Status dictionary
        """
        if not self.ip_address:
            return {
                'status': 'success',
                'message': f'Mock: Speaking on {self.device_name}: "{text}"',
                'device_id': self.device_id,
                'text': text
            }
        # Real implementation would use Sonos API to speak
        return {
            'status': 'success',
            'message': f'Speaking on {self.device_name}',
            'device_id': self.device_id,
            'text': text
        }

    async def set_volume(self, level: int) -> Dict[str, Any]:
        """Set speaker volume (0-100)"""
        if level < 0 or level > 100:
            return {'status': 'error', 'message': 'Volume must be 0-100'}

        self.volume = level
        if not self.ip_address:
            return {
                'status': 'success',
                'message': f'Mock: Volume set to {level}%',
                'device_id': self.device_id,
                'volume': level
            }
        return {
            'status': 'success',
            'device_id': self.device_id,
            'volume': level
        }

    async def get_status(self) -> Dict[str, Any]:
        """Get speaker status"""
        return {
            'status': 'success',
            'device_id': self.device_id,
            'device_name': self.device_name,
            'ip_address': self.ip_address,
            'volume': self.volume,
            'is_playing': self.is_playing,
            'is_connected': bool(self.ip_address)
        }


class SonosManager:
    """Manages Sonos speaker discovery and control"""

    def __init__(self):
        """Initialize Sonos manager"""
        self.devices: Dict[str, SonosDevice] = {}
        self.discover_devices()

    def discover_devices(self):
        """Discover Sonos devices on network"""
        # Mock discovery - in real implementation would use SSDP/UPnP
        default_speaker = SonosDevice(
            device_id='living_room_sonos',
            device_name='Living Room Speaker',
            ip_address=os.environ.get('SONOS_SPEAKER_IP')
        )
        self.devices['living_room_sonos'] = default_speaker

    def get_device(self, device_id: str) -> Optional[SonosDevice]:
        """Get a speaker device by ID"""
        return self.devices.get(device_id)

    def get_all_devices(self) -> Dict[str, SonosDevice]:
        """Get all discovered devices"""
        return self.devices

    async def speak_on_device(self, device_id: str, text: str) -> Dict[str, Any]:
        """Speak text on a specific device"""
        device = self.get_device(device_id)
        if not device:
            return {'status': 'error', 'message': f'Device {device_id} not found'}

        return await device.speak(text)


# Global Sonos manager
_sonos_manager = None


def get_sonos_manager() -> SonosManager:
    """Get or create the global Sonos manager"""
    global _sonos_manager
    if _sonos_manager is None:
        _sonos_manager = SonosManager()
    return _sonos_manager
