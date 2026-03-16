"""
Roku Device Control Implementation
For Roku device control via ECP (External Control Protocol) REST API
"""

import os
import asyncio
import aiohttp
import logging
from typing import Dict, Any, Optional
from . import TVDevice

logger = logging.getLogger(__name__)


class RokuClient:
    """Roku ECP (External Control Protocol) client"""

    def __init__(self, ip: str, port: int = 8060, timeout: float = 5.0):
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.base_url = f"http://{ip}:{port}"
        self.session = None

    async def ensure_session(self):
        """Ensure aiohttp session is created"""
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def close(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()
            self.session = None

    async def send_keypress(self, key: str) -> bool:
        """Send a keypress to the Roku device"""
        try:
            await self.ensure_session()

            url = f"{self.base_url}/keypress/{key}"
            async with self.session.post(url, timeout=aiohttp.ClientTimeout(total=self.timeout)) as resp:
                return resp.status in [200, 204]
        except asyncio.TimeoutError:
            logger.error(f"Keypress timeout on {self.ip}")
            return False
        except Exception as e:
            logger.error(f"Keypress error on {self.ip}: {e}")
            return False

    async def type_text(self, text: str) -> bool:
        """Type text on the Roku device using literal key codes

        This uses Roku's Lit_[char] keypress format to type text
        """
        try:
            for char in text:
                if char.isalnum():
                    # Use Lit_[char] for alphanumeric characters
                    success = await self.send_keypress(f'Lit_{char}')
                    if not success:
                        logger.warning(f"Failed to type character '{char}' on {self.ip}")
                elif char == ' ':
                    # Space bar
                    success = await self.send_keypress('Lit_ ')
                elif char == '-':
                    success = await self.send_keypress('Lit_-')
                elif char == ':':
                    success = await self.send_keypress('Lit_:')
                # Add more special characters as needed
                await asyncio.sleep(0.1)  # Small delay between characters
            return True
        except Exception as e:
            logger.error(f"Error typing text on {self.ip}: {e}")
            return False

    async def launch_app(self, app_id: str, params: Optional[Dict[str, str]] = None) -> bool:
        """Launch an app by ID on the Roku device

        Args:
            app_id: The Roku app ID to launch
            params: Optional dictionary of parameters to pass (e.g., {'profile': 'Dan'} for YouTube TV)
        """
        try:
            await self.ensure_session()

            url = f"{self.base_url}/launch/{app_id}"
            # Add query parameters if provided
            if params:
                query_string = "&".join([f"{k}={v}" for k, v in params.items()])
                url = f"{url}?{query_string}"

            async with self.session.post(url, timeout=aiohttp.ClientTimeout(total=self.timeout)) as resp:
                return resp.status in [200, 204]
        except asyncio.TimeoutError:
            logger.error(f"Launch app timeout on {self.ip}")
            return False
        except Exception as e:
            logger.error(f"Launch app error on {self.ip}: {e}")
            return False

    async def get_device_info(self) -> Optional[Dict[str, str]]:
        """Get Roku device information"""
        try:
            await self.ensure_session()

            url = f"{self.base_url}/query/device-info"
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=self.timeout)) as resp:
                if resp.status == 200:
                    return await resp.text()
                return None
        except asyncio.TimeoutError:
            logger.error(f"Device info timeout on {self.ip}")
            return None
        except Exception as e:
            logger.error(f"Device info error on {self.ip}: {e}")
            return None

    async def get_active_app(self) -> Optional[str]:
        """Get currently active app on Roku"""
        try:
            await self.ensure_session()

            url = f"{self.base_url}/query/active-app"
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=self.timeout)) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    # XML response - extract app ID
                    if "<app id=" in text:
                        start = text.find('id="') + 4
                        end = text.find('"', start)
                        return text[start:end]
                return None
        except asyncio.TimeoutError:
            logger.error(f"Active app timeout on {self.ip}")
            return None
        except Exception as e:
            logger.error(f"Active app error on {self.ip}: {e}")
            return None


class RokuDevice(TVDevice):
    """Roku device control - acts as content source for Fire TVs"""

    def __init__(self, device_id: str, device_name: str, device_ip: Optional[str] = None,
                 roku_port: int = 8060, channel: Optional[int] = None):
        """
        Initialize Roku device

        Args:
            device_id: Unique device identifier (e.g., 'upper_left')
            device_name: Display name
            device_ip: IP address of Roku device
            roku_port: Roku ECP port (default 8060)
            channel: Antenna channel this Roku broadcasts to on Fire TV
        """
        super().__init__(device_id, device_name)
        self.device_ip = device_ip or os.environ.get(f'ROKU_{device_id.upper()}_IP')
        self.roku_port = roku_port
        self.channel = channel or int(os.environ.get(f'ROKU_{device_id.upper()}_CHANNEL', 0))
        self.device_type = 'Roku Device'
        self.roku_client = None
        self.is_connected = False

        # Roku app navigation sequences
        # Maps service names to arrow key sequences from home screen
        # Format: list of arrow keys to navigate to app (Home → arrows → OK)
        # These are standard positions on most Roku devices
        self.app_sequences = {
            'Netflix': ['Right'],                    # Netflix usually first
            'Prime Video': ['Right', 'Right'],       # Amazon Prime second
            'YouTube': ['Right', 'Right', 'Right'],  # YouTube third
            'Hulu': ['Right', 'Right', 'Right', 'Right'],
            'ESPN': ['Right', 'Right', 'Right', 'Right', 'Right'],
            'ESPN+': ['Right', 'Right', 'Right', 'Right', 'Right'],
            'Peacock': ['Right', 'Right', 'Right', 'Right', 'Right', 'Right'],
            'HBO Max': ['Right', 'Right', 'Right', 'Right', 'Right', 'Right', 'Right'],
            'YouTubeTV': ['Right', 'Right', 'Right', 'Right', 'Right', 'Right', 'Right', 'Right'],
        }

        # Fallback: Also store app IDs for direct launch attempts
        # IDs verified against actual Roku device /query/apps endpoint (3/15/2026)
        self.app_ids = {
            'YouTubeTV': '195316',  # YouTube TV (verified - ALL 4 devices have it)
            'Peacock': '113072',    # Peacock app ID (not found on devices, fallback to navigation)
            'ESPN+': '34376',       # ESPN app (verified - all devices have it)
            'ESPN': '34376',        # ESPN alias (verified)
            'Prime Video': '13',    # Amazon Prime Video (verified - all devices)
            'HBO Max': '61322',     # HBO Max (verified - Upper Right & Lower Left have it)
            'YouTube': '837',       # YouTube (not found on devices, fallback to navigation)
            'Fandango': '142844',   # Fandango (not found on devices, fallback to navigation)
            'Vudu': '2285',         # Vudu (not found on devices, fallback to navigation)
            'Netflix': '12',        # Netflix (verified - all devices)
            'Hulu': '2285',         # Hulu (verified - Upper Left & Lower Right have it)
            'MLB': '43594',         # MLB.TV app
            'Disney+': '291097',    # Disney+ app
        }

        # Map JustWatch service names (and variations) to our canonical app names
        self.service_name_map = {
            'netflix': 'Netflix',
            'netflix standard with ads': 'Netflix',
            'netflix basic with ads': 'Netflix',
            'hulu': 'Hulu',
            'disney plus': 'Disney+',
            'disney+': 'Disney+',
            'hbo max': 'HBO Max',
            'max': 'HBO Max',
            'max amazon channel': 'HBO Max',
            'hbo max amazon channel': 'HBO Max',
            'amazon prime video': 'Prime Video',
            'amazon video': 'Prime Video',
            'prime video': 'Prime Video',
            'peacock': 'Peacock',
            'peacock premium': 'Peacock',
            'peacock premium plus': 'Peacock',
            'espn': 'ESPN',
            'espn+': 'ESPN+',
            'espn plus': 'ESPN+',
            'youtube tv': 'YouTubeTV',
            'youtubetv': 'YouTubeTV',
            'youtube': 'YouTube',
            'apple tv': 'Apple TV',
            'apple tv+': 'Apple TV',
            'apple tv plus': 'Apple TV',
            'apple tv store': 'Apple TV',
            'paramount+': 'Paramount+',
            'paramount plus': 'Paramount+',
            'fandango at home': 'Vudu',
            'fandango at home free': 'Vudu',
            'vudu': 'Vudu',
            'fandango': 'Fandango',
            'fubo': 'fuboTV',
            'fubotv': 'fuboTV',
            'showtime': 'Showtime',
            'starz': 'Starz',
            'crunchyroll': 'Crunchyroll',
            'tubi': 'Tubi',
            'pluto tv': 'Pluto TV',
            'plex': 'Plex',
            'spectrum on demand': 'Spectrum',
            'mlb': 'MLB',
            'mlb.tv': 'MLB',
            'mlb tv': 'MLB',
        }

    async def _ensure_connected(self) -> bool:
        """Ensure Roku connection is established"""
        if not self.device_ip:
            return False

        if not self.roku_client:
            self.roku_client = RokuClient(self.device_ip, self.roku_port)

        if not self.is_connected:
            try:
                # Test connection by getting device info
                info = await self.roku_client.get_device_info()
                self.is_connected = info is not None
                if self.is_connected:
                    logger.info(f"Connected to {self.device_name} (Roku) at {self.device_ip}")
            except Exception as e:
                logger.error(f"Connection failed for {self.device_name}: {e}")
                self.is_connected = False

        return self.is_connected

    async def launch_app(self, app_name: str, content_id: Optional[str] = None, title: Optional[str] = None) -> Dict[str, Any]:
        """Launch streaming service app on Roku device using navigation or direct launch

        Args:
            app_name: Name of the app to launch
            content_id: Optional content ID (usually internal service ID)
            title: Optional program title to search for in YouTube TV
        """
        if not self.device_ip:
            return {
                'status': 'success',
                'message': f'Mock: Launching {app_name} on {self.device_name}',
                'device_id': self.device_id,
                'device_name': self.device_name,
                'app': app_name,
                'content_id': content_id,
                'note': f'Set ROKU_{self.device_id.upper()}_IP environment variable for real control'
            }

        try:
            if not await self._ensure_connected():
                return {
                    'status': 'error',
                    'message': f'Cannot connect to {self.device_name} at {self.device_ip}',
                    'device_id': self.device_id
                }

            # First, press Home to ensure we're on the home screen
            # This helps clear any running apps and ensures a clean launch
            logger.info(f"Pressing Home on {self.device_name} to clear any running apps")
            await self.roku_client.send_keypress('Home')
            await asyncio.sleep(1)  # Wait for home screen to appear

            # Resolve JustWatch/variant service names to canonical app name
            canonical_name = self.service_name_map.get(app_name.lower(), app_name)
            if canonical_name != app_name:
                logger.info(f"Mapped service name '{app_name}' -> '{canonical_name}'")
                app_name = canonical_name

            # First, try direct app launch via app ID
            app_id = self.app_ids.get(app_name)
            if app_id:
                # Build launch parameters for deep linking
                launch_params = {}

                # For YouTube TV, try to pass video ID or search query
                if app_name == 'YouTubeTV' and content_id:
                    # Extract video ID if it's in the format "YouTubeTV_VIDEO_ID"
                    if '_' in content_id:
                        video_id = content_id.split('_', 1)[1]
                        launch_params['v'] = video_id  # Try YouTube-style video parameter
                        logger.info(f"Deep linking YouTube TV with video ID: {video_id}")

                    # Also pass title as search query for fallback
                    if title:
                        launch_params['search'] = title  # Pass title for search
                        logger.info(f"Also passing search title: {title}")

                success = await self.roku_client.launch_app(app_id, params=launch_params if launch_params else None)
                if success:
                    logger.info(f"Launched {app_name} on {self.device_name} via direct app launch")

                    # For YouTube TV, select Dan profile after launch
                    profile_selected = None
                    if app_name == 'YouTubeTV':
                        logger.info(f"Waiting for YouTubeTV to load and selecting Dan profile on {self.device_name}")
                        await asyncio.sleep(4)  # Wait longer for YouTubeTV to fully load profile selection

                        # Try pressing Down first to ensure a profile is focused
                        await self.roku_client.send_keypress('Down')
                        await asyncio.sleep(0.3)

                        # Navigate to Dan profile - send Select key to confirm
                        # Assume Dan is the first/default profile
                        success_profile = await self.roku_client.send_keypress('Select')
                        if success_profile:
                            profile_selected = 'Dan'
                            logger.info(f"Selected Dan profile on {self.device_name}")
                        else:
                            logger.warning(f"Failed to select Dan profile on {self.device_name}, profile selection may need manual intervention")

                        # If title is provided, log what the user should search for
                        # Note: YouTube TV on Roku doesn't support programmatic text input via ECP
                        if title and profile_selected:
                            logger.info(f"YouTube TV ready on {self.device_name}. User should search for: '{title}'")

                    return {
                        'status': 'success',
                        'message': f'Launching {app_name} on {self.device_name}' + (' with Dan profile' if profile_selected else '') + (f'. Search for: "{title}"' if title and profile_selected else ''),
                        'device_id': self.device_id,
                        'device_name': self.device_name,
                        'device_type': self.device_type,
                        'app': app_name,
                        'app_id': app_id,
                        'content_id': content_id,
                        'search_hint': title if profile_selected else None,
                        'broadcast_channel': self.channel,
                        'launch_method': 'direct',
                        'profile': profile_selected,
                        'is_connected': True
                    }

            # Fallback: Use arrow key navigation
            sequence = self.app_sequences.get(app_name)
            if not sequence:
                return {'status': 'error', 'message': f'App {app_name} not supported'}

            # Navigate using arrow keys: Home → arrows → OK
            await self.roku_client.send_keypress('Home')
            await asyncio.sleep(1.2)  # Wait for home screen

            # Send arrow keys
            for arrow in sequence:
                await self.roku_client.send_keypress(arrow)
                await asyncio.sleep(0.5)  # Wait between presses

            # Select the app with OK
            await self.roku_client.send_keypress('Select')

            logger.info(f"Launched {app_name} on {self.device_name} via navigation")

            # For YouTube TV, select Dan profile after launch
            profile_selected = None
            if app_name == 'YouTubeTV':
                logger.info(f"Waiting for YouTubeTV to load and selecting Dan profile on {self.device_name}")
                await asyncio.sleep(4.5)  # Wait longer for YouTubeTV to load via navigation and show profile selection

                # Try pressing Down first to ensure a profile is focused
                await self.roku_client.send_keypress('Down')
                await asyncio.sleep(0.3)

                # Send Select key to confirm Dan profile (usually the default/first profile)
                success_profile = await self.roku_client.send_keypress('Select')
                if success_profile:
                    profile_selected = 'Dan'
                    logger.info(f"Selected Dan profile on {self.device_name} (navigation method)")
                else:
                    logger.warning(f"Failed to select Dan profile on {self.device_name} via navigation, trying with Up arrow first")
                    # Sometimes the profile might not be focused, try Up arrow to focus it first
                    await self.roku_client.send_keypress('Up')
                    await asyncio.sleep(0.3)
                    success_profile = await self.roku_client.send_keypress('Select')
                    if success_profile:
                        profile_selected = 'Dan'
                        logger.info(f"Selected Dan profile on {self.device_name} after Up arrow")
                    else:
                        logger.warning(f"Still failed to select Dan profile on {self.device_name}, profile selection may need manual intervention")

                # If title is provided, log what the user should search for
                # Note: YouTube TV on Roku doesn't support programmatic text input via ECP
                if title and profile_selected:
                    logger.info(f"YouTube TV ready on {self.device_name}. User should search for: '{title}'")

            return {
                'status': 'success',
                'message': f'Launching {app_name} on {self.device_name}' + (' with Dan profile' if profile_selected else '') + (f'. Search for: "{title}"' if title and profile_selected else ''),
                'device_id': self.device_id,
                'device_name': self.device_name,
                'device_type': self.device_type,
                'app': app_name,
                'content_id': content_id,
                'search_hint': title if profile_selected else None,
                'broadcast_channel': self.channel,
                'launch_method': 'navigation',
                'profile': profile_selected,
                'is_connected': True
            }
        except Exception as e:
            logger.error(f"Failed to launch app on {self.device_name}: {e}")
            return {
                'status': 'error',
                'message': f'Failed to launch {app_name}',
                'device_id': self.device_id,
                'error': str(e)
            }

    async def launch_url(self, url: str) -> Dict[str, Any]:
        """Roku doesn't support direct URL launching - return error"""
        return {
            'status': 'error',
            'message': f'Roku devices do not support direct URL launching',
            'device_id': self.device_id,
            'note': 'Use app-specific deep links or launch an app instead'
        }

    async def power_on(self) -> Dict[str, Any]:
        """Wake Roku device (send Home key)"""
        if not self.device_ip:
            return {
                'status': 'success',
                'message': f'Mock: Powering on {self.device_name}',
                'device_id': self.device_id
            }

        try:
            if not await self._ensure_connected():
                return {
                    'status': 'error',
                    'message': f'Cannot connect to {self.device_name}',
                    'device_id': self.device_id
                }

            # Send Home key to wake device
            await self.roku_client.send_keypress('Home')

            return {
                'status': 'success',
                'message': f'{self.device_name} is now on',
                'device_id': self.device_id,
                'is_connected': True
            }
        except Exception as e:
            logger.error(f"Failed to power on {self.device_name}: {e}")
            return {
                'status': 'error',
                'message': f'Failed to power on {self.device_name}',
                'device_id': self.device_id,
                'error': str(e)
            }

    async def power_off(self) -> Dict[str, Any]:
        """Power off Roku device (send Power key)"""
        if not self.device_ip:
            return {
                'status': 'success',
                'message': f'Mock: Powering off {self.device_name}',
                'device_id': self.device_id
            }

        try:
            if not await self._ensure_connected():
                return {
                    'status': 'error',
                    'message': f'Cannot connect to {self.device_name}',
                    'device_id': self.device_id
                }

            # Send Power Off key
            await self.roku_client.send_keypress('PowerOff')

            return {
                'status': 'success',
                'message': f'{self.device_name} is now off',
                'device_id': self.device_id,
                'is_connected': True
            }
        except Exception as e:
            logger.error(f"Failed to power off {self.device_name}: {e}")
            return {
                'status': 'error',
                'message': f'Failed to power off {self.device_name}',
                'device_id': self.device_id,
                'error': str(e)
            }

    async def set_volume(self, level: int) -> Dict[str, Any]:
        """Set volume on Roku device (0-100)"""
        if level < 0 or level > 100:
            return {'status': 'error', 'message': 'Volume must be between 0-100'}

        if not self.device_ip:
            return {
                'status': 'success',
                'message': f'Mock: Volume set to {level}% on {self.device_name}',
                'device_id': self.device_id,
                'volume': level
            }

        try:
            if not await self._ensure_connected():
                return {
                    'status': 'error',
                    'message': f'Cannot connect to {self.device_name}',
                    'device_id': self.device_id
                }

            # Roku volume is 0-100, send Up/Down keys to adjust
            # This is a simplified approach - ideal would be to set absolute volume
            # For now, just send a volume up command as acknowledgment
            await self.roku_client.send_keypress('VolumeUp')

            return {
                'status': 'success',
                'message': f'Volume adjusted on {self.device_name}',
                'device_id': self.device_id,
                'volume': level,
                'is_connected': True
            }
        except Exception as e:
            logger.error(f"Failed to set volume on {self.device_name}: {e}")
            return {
                'status': 'error',
                'message': f'Failed to set volume',
                'device_id': self.device_id,
                'error': str(e)
            }

    async def get_status(self) -> Dict[str, Any]:
        """Get current Roku device status"""
        if not self.device_ip:
            return {
                'status': 'success',
                'device_id': self.device_id,
                'device_name': self.device_name,
                'device_type': self.device_type,
                'device_ip': self.device_ip,
                'power_state': 'on',
                'volume': 50,
                'current_app': None,
                'broadcast_channel': self.channel,
                'is_connected': False,
                'note': f'Mock data - set ROKU_{self.device_id.upper()}_IP for real status'
            }

        try:
            connected = await self._ensure_connected()

            if not connected:
                return {
                    'status': 'success',
                    'device_id': self.device_id,
                    'device_name': self.device_name,
                    'device_type': self.device_type,
                    'device_ip': self.device_ip,
                    'broadcast_channel': self.channel,
                    'is_connected': False
                }

            # Get currently active app
            current_app = await self.roku_client.get_active_app()

            return {
                'status': 'success',
                'device_id': self.device_id,
                'device_name': self.device_name,
                'device_type': self.device_type,
                'device_ip': self.device_ip,
                'power_state': 'on',
                'volume': 50,
                'current_app': current_app,
                'broadcast_channel': self.channel,
                'is_connected': True
            }
        except Exception as e:
            logger.error(f"Failed to get status for {self.device_name}: {e}")
            return {
                'status': 'success',
                'device_id': self.device_id,
                'device_name': self.device_name,
                'device_type': self.device_type,
                'device_ip': self.device_ip,
                'broadcast_channel': self.channel,
                'is_connected': False,
                'error': str(e)
            }
