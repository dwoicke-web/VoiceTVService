"""
TV Control module - Base classes for controlling TV devices
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class TVDevice(ABC):
    """Abstract base class for TV control implementations"""

    def __init__(self, device_id: str, device_name: str):
        """
        Initialize TV device

        Args:
            device_id: Unique device identifier
            device_name: Human-readable device name
        """
        self.device_id = device_id
        self.device_name = device_name
        self.is_connected = False

    @abstractmethod
    async def launch_app(self, app_name: str, content_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Launch an app on the TV (streaming service)

        Args:
            app_name: Name of the app to launch (e.g., 'YouTubeTV', 'Peacock')
            content_id: Optional content ID to play after launching app

        Returns:
            Dictionary with status and response details
        """
        pass

    @abstractmethod
    async def launch_url(self, url: str) -> Dict[str, Any]:
        """
        Launch a URL on the TV

        Args:
            url: URL to open on the TV

        Returns:
            Dictionary with status and response details
        """
        pass

    @abstractmethod
    async def power_on(self) -> Dict[str, Any]:
        """Power on the TV"""
        pass

    @abstractmethod
    async def power_off(self) -> Dict[str, Any]:
        """Power off the TV"""
        pass

    @abstractmethod
    async def set_volume(self, level: int) -> Dict[str, Any]:
        """
        Set volume level

        Args:
            level: Volume level 0-100

        Returns:
            Dictionary with status and response details
        """
        pass

    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        """Get current TV status"""
        pass


class TVControlManager:
    """Manages all TV devices and control operations"""

    def __init__(self):
        """Initialize TV control manager"""
        self.devices: Dict[str, TVDevice] = {}

    def register_device(self, device: TVDevice) -> None:
        """Register a TV device"""
        self.devices[device.device_id] = device

    def get_device(self, device_id: str) -> Optional[TVDevice]:
        """Get a registered device by ID"""
        return self.devices.get(device_id)

    async def launch_content(self, device_id: str, app_name: str, content_id: str) -> Dict[str, Any]:
        """Launch content on a specific TV"""
        device = self.get_device(device_id)
        if not device:
            return {'status': 'error', 'message': f'Device {device_id} not found'}

        return await device.launch_app(app_name, content_id)


# Global TV control manager instance
_tv_manager = None


def get_tv_manager() -> TVControlManager:
    """Get or create the global TV control manager"""
    global _tv_manager
    if _tv_manager is None:
        _tv_manager = TVControlManager()
    return _tv_manager
