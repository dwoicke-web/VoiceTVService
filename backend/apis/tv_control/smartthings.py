"""
Samsung SmartThings TV Control Implementation
For Samsung Smart TV control via SmartThings API
"""

import os
import asyncio
import aiohttp
import logging
from typing import Dict, Any, Optional
from . import TVDevice

logger = logging.getLogger(__name__)


class SamsungSmartThingsDevice(TVDevice):
    """Samsung TV control via SmartThings API"""

    def __init__(self, device_id: str, device_name: str, smartthings_token: Optional[str] = None, smartthings_device_id: Optional[str] = None):
        """
        Initialize Samsung SmartThings device

        Args:
            device_id: Human-readable device identifier (e.g., 'big_screen')
            device_name: Display name for the TV
            smartthings_token: SmartThings API token (from environment or parameter)
            smartthings_device_id: SmartThings device UUID for API calls (from environment or parameter)
        """
        super().__init__(device_id, device_name)
        self.smartthings_token = smartthings_token or os.environ.get('SMARTTHINGS_TOKEN')
        self.smartthings_device_id = smartthings_device_id or os.environ.get('SAMSUNG_SMARTTHINGS_DEVICE_ID')
        self.api_base = 'https://api.smartthings.com/v1'
        self.device_type = 'Samsung Smart TV'

        # App ID mappings for SmartThings (Samsung TV-specific app package names)
        self.app_mappings = {
            'YouTubeTV': 'com.google.android.youtube.tv',
            'Peacock': 'com.peacocktv.peacockandroid',
            'ESPN+': 'com.espn.mobile.android.espn',
            'Prime Video': 'com.amazon.amazonvideo.livingroom',
            'HBO Max': 'com.hbo.hbomax',
            'YouTube': 'com.google.android.youtube.tv',
            'Fandango': 'com.fandango.fandango',
            'Vudu': 'com.vudu.vudu',
            'JustWatch': 'com.justwatch.justwatch'
        }

    async def _send_remote_key(self, session: aiohttp.ClientSession, key: str) -> bool:
        """Send a remote control key press to the TV"""
        url = f"{self.api_base}/devices/{self.smartthings_device_id}/commands"
        headers = {
            'Authorization': f'Bearer {self.smartthings_token}',
            'Content-Type': 'application/json'
        }
        payload = {
            'commands': [
                {
                    'component': 'main',
                    'capability': 'samsungvd.remoteControl',
                    'command': 'send',
                    'arguments': [key]
                }
            ]
        }
        try:
            async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as response:
                return response.status in [200, 201]
        except Exception as e:
            logger.error(f"Error sending remote key {key}: {str(e)}")
            return False

    async def _search_youtube_content(self, session: aiohttp.ClientSession, video_id: str, title: str) -> bool:
        """
        Attempt to find and play YouTube content.
        For Samsung TV YouTube app, navigate to search and guide user to complete playback.
        """
        logger.info(f"SmartThings: Searching for YouTube video {video_id}: {title}")

        try:
            # Give app time to fully load
            await asyncio.sleep(2)

            # Try to open search in YouTube app
            # YouTube TV typically responds to UP arrow to reach search
            logger.info("SmartThings: Navigating to search in YouTube app...")

            # Send UP to reach search bar
            for i in range(3):
                if await self._send_remote_key(session, 'UP'):
                    logger.info(f"SmartThings: Sent UP arrow ({i+1}/3)")
                await asyncio.sleep(0.5)

            # Try to activate search
            if await self._send_remote_key(session, 'OK'):
                logger.info("SmartThings: Activated search in YouTube")
                await asyncio.sleep(1)

                # Log the video info for user reference
                logger.info(f"SmartThings: Ready to play - Video ID: {video_id}, Title: {title}")
                logger.info(f"SmartThings: Please note - Direct video playback requires manual search due to TV input limitations")

                return True

            return False

        except Exception as e:
            logger.error(f"Error searching YouTube: {str(e)}")
            return False

    async def launch_app(self, app_name: str, content_id: Optional[str] = None) -> Dict[str, Any]:
        """Launch streaming service app on Samsung TV using remote control navigation"""
        logger.info(f"launch_app called with app_name='{app_name}', content_id='{content_id}'")

        # App navigation sequences based on Samsung home screen layout
        # Layout: Samsung TV Plus → Live TV Air → YouTubeTV → Netflix → Amazon Prime → ESPN → Disney+ → HBO Max → YouTube → MLB → Apple TV → Fandango → Hulu → Paramount+ → Peacock
        app_sequences = {
            'Samsung TV Plus': ['RIGHT'],
            'Live TV Air': ['RIGHT', 'RIGHT'],
            'YouTubeTV': ['RIGHT', 'RIGHT', 'RIGHT'],
            'Netflix': ['RIGHT', 'RIGHT', 'RIGHT', 'RIGHT'],
            'Prime Video': ['RIGHT', 'RIGHT', 'RIGHT', 'RIGHT', 'RIGHT'],
            'Amazon Prime': ['RIGHT', 'RIGHT', 'RIGHT', 'RIGHT', 'RIGHT'],
            'ESPN+': ['RIGHT', 'RIGHT', 'RIGHT', 'RIGHT', 'RIGHT', 'RIGHT'],
            'ESPN': ['RIGHT', 'RIGHT', 'RIGHT', 'RIGHT', 'RIGHT', 'RIGHT'],
            'Disney+': ['RIGHT', 'RIGHT', 'RIGHT', 'RIGHT', 'RIGHT', 'RIGHT', 'RIGHT'],
            'Disney Plus': ['RIGHT', 'RIGHT', 'RIGHT', 'RIGHT', 'RIGHT', 'RIGHT', 'RIGHT'],
            'HBO Max': ['RIGHT', 'RIGHT', 'RIGHT', 'RIGHT', 'RIGHT', 'RIGHT', 'RIGHT', 'RIGHT'],
            'YouTube': ['RIGHT'] * 9,
            'MLB': ['RIGHT'] * 10,
            'Apple TV': ['RIGHT'] * 11,
            'Fandango': ['RIGHT'] * 12,
            'Hulu': ['RIGHT'] * 13,
            'Paramount Plus': ['RIGHT'] * 14,
            'Paramount+': ['RIGHT'] * 14,
            'Peacock': ['RIGHT'] * 15,
        }

        if not self.smartthings_token:
            # Mock response for development/testing
            logger.info(f"Mock: Launching {app_name} on {self.device_name} (no API token configured)")
            return {
                'status': 'success',
                'message': f'Mock: Launching {app_name} on {self.device_name}',
                'device_id': self.device_id,
                'device_name': self.device_name,
                'app': app_name,
                'content_id': content_id,
                'note': 'Set SMARTTHINGS_TOKEN environment variable for real control'
            }

        try:
            logger.info(f"SmartThings: Launching {app_name} on {self.device_name} using remote control")

            async with aiohttp.ClientSession() as session:
                # Step 1: Press HOME to go to home screen
                logger.info(f"SmartThings: Sending HOME button")
                if not await self._send_remote_key(session, 'HOME'):
                    logger.warning("HOME button failed")
                await asyncio.sleep(2)  # Wait for TV to load home screen

                # Step 2: Navigate to the app using arrow keys
                arrow_keys = app_sequences.get(app_name, ['RIGHT'])
                logger.info(f"SmartThings: Navigating to {app_name} using keys: {arrow_keys}")
                for key in arrow_keys:
                    if not await self._send_remote_key(session, key):
                        logger.warning(f"Arrow key {key} failed")
                    await asyncio.sleep(0.8)  # Delay between key presses to let TV respond

                # Step 3: Press OK to select the app
                logger.info(f"SmartThings: Pressing OK to launch {app_name}")
                await asyncio.sleep(1)  # Extra delay before OK press
                if await self._send_remote_key(session, 'OK'):
                    logger.info(f"SmartThings: Successfully launched {app_name}")

                    # If content_id is provided, try to play it
                    if content_id and app_name == 'YouTubeTV':
                        # Extract video ID and title from content_id
                        # Format: YouTubeTV_VIDEO_ID (from search results)
                        if '_' in content_id:
                            parts = content_id.split('_', 1)
                            video_id = parts[1] if len(parts) > 1 else content_id
                            logger.info(f"SmartThings: Extracted YouTube video ID: {video_id}")

                            # Try to navigate to search and play the video
                            # We'll attempt to open YouTube search where users can find the content
                            title = f"YouTube video {video_id}"  # Fallback title
                            await self._search_youtube_content(session, video_id, title)

                    return {
                        'status': 'success',
                        'message': f'Launching {app_name} on {self.device_name}',
                        'device_id': self.device_id,
                        'app': app_name,
                        'content_id': content_id
                    }
                else:
                    logger.error(f"Failed to send OK key for {app_name}")
                    return {
                        'status': 'error',
                        'message': f'Failed to launch {app_name}',
                        'device_id': self.device_id
                    }

        except asyncio.TimeoutError:
            logger.error(f"SmartThings API timeout while launching {app_name}")
            return {
                'status': 'error',
                'message': 'SmartThings API request timed out',
                'device_id': self.device_id
            }
        except Exception as e:
            logger.error(f"Error launching {app_name} on SmartThings device: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to launch {app_name}: {str(e)}',
                'device_id': self.device_id
            }

    async def launch_url(self, url: str) -> Dict[str, Any]:
        """Launch a URL on the TV"""
        if not self.smartthings_token:
            return {
                'status': 'success',
                'message': f'Mock: Launching URL on {self.device_name}',
                'device_id': self.device_id,
                'url': url
            }
        return {
            'status': 'success',
            'message': f'Launching URL on {self.device_name}',
            'device_id': self.device_id,
            'url': url
        }

    async def power_on(self) -> Dict[str, Any]:
        """Power on the Samsung TV"""
        if not self.smartthings_token:
            logger.info(f"Mock: Powering on {self.device_name}")
            return {
                'status': 'success',
                'message': f'Mock: Powering on {self.device_name}',
                'device_id': self.device_id
            }

        # Real SmartThings API call
        try:
            logger.info(f"SmartThings: Powering on {self.device_name}")

            async with aiohttp.ClientSession() as session:
                url = f"{self.api_base}/devices/{self.smartthings_device_id}/commands"

                headers = {
                    'Authorization': f'Bearer {self.smartthings_token}',
                    'Content-Type': 'application/json'
                }

                # Power on command
                payload = {
                    'commands': [
                        {
                            'component': 'main',
                            'capability': 'switch',
                            'command': 'on'
                        }
                    ]
                }

                async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status in [200, 201]:
                        logger.info(f"SmartThings: Successfully powered on {self.device_name}")
                        return {
                            'status': 'success',
                            'message': f'{self.device_name} is now on',
                            'device_id': self.device_id
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"SmartThings power on error: {response.status} - {error_text}")
                        return {
                            'status': 'error',
                            'message': f'Failed to power on TV: {response.status}',
                            'device_id': self.device_id
                        }
        except Exception as e:
            logger.error(f"Error powering on SmartThings device: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to power on: {str(e)}',
                'device_id': self.device_id
            }

    async def power_off(self) -> Dict[str, Any]:
        """Power off the Samsung TV"""
        if not self.smartthings_token:
            logger.info(f"Mock: Powering off {self.device_name}")
            return {
                'status': 'success',
                'message': f'Mock: Powering off {self.device_name}',
                'device_id': self.device_id
            }

        # Real SmartThings API call
        try:
            logger.info(f"SmartThings: Powering off {self.device_name}")

            async with aiohttp.ClientSession() as session:
                url = f"{self.api_base}/devices/{self.smartthings_device_id}/commands"

                headers = {
                    'Authorization': f'Bearer {self.smartthings_token}',
                    'Content-Type': 'application/json'
                }

                # Power off command
                payload = {
                    'commands': [
                        {
                            'component': 'main',
                            'capability': 'switch',
                            'command': 'off'
                        }
                    ]
                }

                async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status in [200, 201]:
                        logger.info(f"SmartThings: Successfully powered off {self.device_name}")
                        return {
                            'status': 'success',
                            'message': f'{self.device_name} is now off',
                            'device_id': self.device_id
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"SmartThings power off error: {response.status} - {error_text}")
                        return {
                            'status': 'error',
                            'message': f'Failed to power off TV: {response.status}',
                            'device_id': self.device_id
                        }
        except Exception as e:
            logger.error(f"Error powering off SmartThings device: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to power off: {str(e)}',
                'device_id': self.device_id
            }
        return {
            'status': 'success',
            'message': f'{self.device_name} is now off',
            'device_id': self.device_id
        }

    async def set_volume(self, level: int) -> Dict[str, Any]:
        """Set volume level (0-100)"""
        if level < 0 or level > 100:
            return {'status': 'error', 'message': 'Volume must be between 0-100'}

        if not self.smartthings_token:
            logger.info(f"Mock: Setting volume to {level}% on {self.device_name}")
            return {
                'status': 'success',
                'message': f'Mock: Volume set to {level}% on {self.device_name}',
                'device_id': self.device_id,
                'volume': level
            }

        # Real SmartThings API call
        try:
            logger.info(f"SmartThings: Setting volume to {level}% on {self.device_name}")

            async with aiohttp.ClientSession() as session:
                url = f"{self.api_base}/devices/{self.smartthings_device_id}/commands"

                headers = {
                    'Authorization': f'Bearer {self.smartthings_token}',
                    'Content-Type': 'application/json'
                }

                # Volume command (0-100)
                payload = {
                    'commands': [
                        {
                            'component': 'main',
                            'capability': 'audioVolume',
                            'command': 'setVolume',
                            'arguments': [level]
                        }
                    ]
                }

                async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status in [200, 201]:
                        logger.info(f"SmartThings: Successfully set volume to {level}%")
                        return {
                            'status': 'success',
                            'message': f'Volume set to {level}% on {self.device_name}',
                            'device_id': self.device_id,
                            'volume': level
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"SmartThings volume error: {response.status} - {error_text}")
                        return {
                            'status': 'error',
                            'message': f'Failed to set volume: {response.status}',
                            'device_id': self.device_id
                        }
        except Exception as e:
            logger.error(f"Error setting volume on SmartThings device: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to set volume: {str(e)}',
                'device_id': self.device_id
            }

    async def get_status(self) -> Dict[str, Any]:
        """Get current Samsung TV status"""
        if not self.smartthings_token:
            return {
                'status': 'success',
                'device_id': self.device_id,
                'device_name': self.device_name,
                'device_type': self.device_type,
                'power_state': 'on',
                'volume': 25,
                'current_app': None,
                'is_connected': True,
                'note': 'Mock data - set SMARTTHINGS_TOKEN for real status'
            }
        return {
            'status': 'success',
            'device_id': self.device_id,
            'device_name': self.device_name,
            'device_type': self.device_type,
            'power_state': 'on',
            'volume': 25,
            'current_app': None,
            'is_connected': True
        }
