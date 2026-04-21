"""
Amazon Fire TV Control Implementation
For Fire TV device control via ADB (Android Debug Bridge)
Uses adb-shell library for proper ADB protocol with RSA authentication
Uses Wake-on-LAN for powering on sleeping devices

Each ADB operation creates a fresh connection and closes it when done.
This avoids stale connection issues with network-based ADB.
"""

import os
import asyncio
import logging
import socket
from typing import Dict, Any, Optional
from pathlib import Path
from contextlib import contextmanager
from . import TVDevice

logger = logging.getLogger(__name__)

# MAC address mapping for Wake-on-LAN
FIRE_TV_MAC_ADDRESSES = {
    '192.168.4.80': '08:97:98:20:57:a5',   # Upper Left
    '192.168.4.93': '08:97:98:20:57:a4',   # Lower Left
    '192.168.4.78': '08:97:98:20:68:da',   # Upper Right
    '192.168.4.108': '08:97:98:20:57:94',  # Lower Right
}

# RSA key path for ADB authentication
ADB_KEY_PATH = Path.home() / '.android' / 'adbkey'

# Cache the signer object (keys don't change)
_cached_signer = None


def _send_wol(mac_address: str):
    """Send Wake-on-LAN magic packet to wake a sleeping device"""
    mac_bytes = bytes.fromhex(mac_address.replace(':', '').replace('-', ''))
    magic_packet = b'\xff' * 6 + mac_bytes * 16
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.sendto(magic_packet, ('255.255.255.255', 9))
    sock.sendto(magic_packet, ('192.168.4.255', 9))
    sock.close()
    logger.info(f"Sent Wake-on-LAN packet to {mac_address}")


def _get_signer():
    """Get or create RSA signer for ADB authentication"""
    global _cached_signer
    if _cached_signer:
        return _cached_signer

    from adb_shell.auth.keygen import keygen
    from adb_shell.auth.sign_pythonrsa import PythonRSASigner

    key_dir = ADB_KEY_PATH.parent
    key_dir.mkdir(parents=True, exist_ok=True)

    if not ADB_KEY_PATH.exists():
        keygen(str(ADB_KEY_PATH))
        logger.info(f"Generated ADB RSA keys at {ADB_KEY_PATH}")

    with open(str(ADB_KEY_PATH), 'r') as f:
        priv_key = f.read()

    pub_key_path = str(ADB_KEY_PATH) + '.pub'
    if os.path.exists(pub_key_path):
        with open(pub_key_path, 'r') as f:
            pub_key = f.read()
    else:
        pub_key = ''

    _cached_signer = PythonRSASigner(pub_key, priv_key)
    return _cached_signer


@contextmanager
def _adb_connection(ip: str, port: int = 5555, timeout: float = 10.0):
    """Context manager that creates a fresh ADB connection and closes it when done.

    Usage:
        with _adb_connection('192.168.4.80') as device:
            device.shell('input keyevent KEYCODE_SLEEP')
    """
    from adb_shell.adb_device import AdbDeviceTcp

    signer = _get_signer()
    device = AdbDeviceTcp(ip, port, default_transport_timeout_s=timeout)

    try:
        device.connect(rsa_keys=[signer], auth_timeout_s=timeout)
        logger.info(f"ADB connected to {ip}:{port}")
        yield device
    finally:
        try:
            device.close()
        except Exception:
            pass


def _run_adb_command(ip: str, cmd: str, port: int = 5555, timeout: float = 10.0) -> str:
    """Run a single ADB shell command with a fresh connection (synchronous)"""
    with _adb_connection(ip, port, timeout) as device:
        result = device.shell(cmd, timeout_s=timeout)
        return result.strip() if result else ""


def _run_adb_commands(ip: str, commands: list, port: int = 5555, timeout: float = 10.0) -> list:
    """Run multiple ADB shell commands on a single connection (synchronous)"""
    results = []
    with _adb_connection(ip, port, timeout) as device:
        for cmd, delay in commands:
            result = device.shell(cmd, timeout_s=timeout)
            results.append(result.strip() if result else "")
            if delay > 0:
                import time
                time.sleep(delay)
    return results


class FireTVDevice(TVDevice):
    """Amazon Fire TV device control"""

    def __init__(self, device_id: str, device_name: str, device_ip: Optional[str] = None,
                 adb_port: int = 5555):
        super().__init__(device_id, device_name)
        self.device_ip = device_ip or os.environ.get(f'FIRETV_{device_id.upper()}_IP')
        self.adb_port = adb_port
        self.device_type = 'Amazon Fire TV'
        self.is_connected = False

        # App package name mappings for Fire TV
        self.app_packages = {
            'YouTubeTV': 'com.amazon.firetv.youtube.tv',
            'Peacock': 'com.peacocktv.peacockandroid',
            'ESPN+': 'com.espn.gtv',
            'Prime Video': 'com.amazon.amazonvideo.livingroom',
            'HBO Max': 'com.hbo.hbomax',
            'YouTube': 'com.google.android.youtube.tv',
            'Fandango': 'com.fandango',
            'Vudu': 'com.vudu',
            'JustWatch': 'com.justwatch.justwatch'
        }

    async def _run_cmd(self, cmd: str) -> str:
        """Run a single ADB command (async wrapper around synchronous ADB)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, _run_adb_command, self.device_ip, cmd, self.adb_port, 10.0
        )

    async def _run_cmds(self, commands: list) -> list:
        """Run multiple ADB commands on a single connection (async wrapper)

        commands: list of (cmd_string, delay_after_seconds) tuples
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, _run_adb_commands, self.device_ip, commands, self.adb_port, 10.0
        )

    async def close_app(self, app_name: str) -> bool:
        """Close/kill an app on Fire TV"""
        try:
            if not self.device_ip:
                return False
            package = self.app_packages.get(app_name)
            if not package:
                return False
            await self._run_cmd(f'am force-stop {package}')
            logger.info(f"Closed {app_name} on {self.device_name}")
            return True
        except Exception as e:
            logger.warning(f"Failed to close {app_name} on {self.device_name}: {e}")
            return False

    async def launch_app(self, app_name: str, content_id: Optional[str] = None) -> Dict[str, Any]:
        """Launch streaming service app on Fire TV"""
        if not self.device_ip:
            return {'status': 'error', 'message': f'No IP configured for {self.device_name}',
                    'device_id': self.device_id}
        try:
            package = self.app_packages.get(app_name)
            if not package:
                return {'status': 'error', 'message': f'App {app_name} not supported'}
            await self._run_cmd(f'am start {package}')
            logger.info(f"Launched {app_name} on {self.device_name}")
            return {
                'status': 'success', 'message': f'Launching {app_name} on {self.device_name}',
                'device_id': self.device_id, 'device_name': self.device_name,
                'app': app_name, 'package': package, 'content_id': content_id,
                'is_connected': True
            }
        except Exception as e:
            logger.error(f"Failed to launch app on {self.device_name}: {e}")
            return {'status': 'error', 'message': f'Failed to launch {app_name}',
                    'device_id': self.device_id, 'error': str(e)}

    async def launch_url(self, url: str) -> Dict[str, Any]:
        """Launch a URL on Fire TV"""
        if not self.device_ip:
            return {'status': 'error', 'message': f'No IP configured for {self.device_name}',
                    'device_id': self.device_id}
        try:
            await self._run_cmd(f'am start -a android.intent.action.VIEW -d "{url}"')
            return {
                'status': 'success', 'message': f'Launching URL on {self.device_name}',
                'device_id': self.device_id, 'url': url, 'is_connected': True
            }
        except Exception as e:
            logger.error(f"Failed to launch URL on {self.device_name}: {e}")
            return {'status': 'error', 'message': f'Failed to launch URL',
                    'device_id': self.device_id, 'error': str(e)}

    async def tune_channel(self, channel_name: str) -> Dict[str, Any]:
        """Tune to a YouTube TV channel on Fire TV via Cobalt deep link.

        Sequence (per feedback memory — fresh launch is required):
          1. Map national network names to KC affiliates
          2. Look up videoId from ytv_channel_mappings.json
          3. `am force-stop com.amazon.firetv.youtube.tv`
          4. `am start -a VIEW -d https://tv.youtube.com/watch/<videoId> -n <pkg>/dev.cobalt.app.MainActivity`

        No keypress fallback — if the videoId is missing or the intent fails,
        we return an error so the caller can surface it.
        """
        kc_affiliate_map = {
            'ABC': 'KMBC',
            'NBC': 'KSHB',
            'CBS': 'KCTV 5',
            'FOX': 'FOX 4',
        }
        channel_name = kc_affiliate_map.get(channel_name.upper(), channel_name)

        if not self.device_ip:
            return {
                'status': 'success',
                'message': f'Mock: Tuning to {channel_name} on {self.device_name}',
                'device_id': self.device_id,
                'channel': channel_name,
            }

        from apis.tv_control.ytv_channels import get_mapper
        mapper = get_mapper()
        video_id = mapper.get_video_id(channel_name)
        if not video_id:
            return {
                'status': 'error',
                'message': f'No YouTube TV videoId mapped for channel "{channel_name}"',
                'device_id': self.device_id,
                'channel': channel_name,
            }

        package = self.app_packages['YouTubeTV']
        activity = f'{package}/dev.cobalt.app.MainActivity'
        url = f'https://tv.youtube.com/watch/{video_id}'

        try:
            await self._run_cmd(f'am force-stop {package}')
            await asyncio.sleep(1.0)
            start_cmd = f"am start -a android.intent.action.VIEW -d '{url}' -n {activity}"
            output = await self._run_cmd(start_cmd)

            if 'Error' in output or 'Exception' in output:
                logger.error(f"YT TV deep link failed on {self.device_name}: {output}")
                return {
                    'status': 'error',
                    'message': f'Failed to tune to {channel_name}',
                    'device_id': self.device_id,
                    'channel': channel_name,
                    'error': output,
                }

            logger.info(f"Tuned to {channel_name} (videoId={video_id}) on {self.device_name}")
            return {
                'status': 'success',
                'message': f'Tuning to {channel_name} on {self.device_name}',
                'device_id': self.device_id,
                'device_name': self.device_name,
                'device_type': self.device_type,
                'channel': channel_name,
                'app': 'YouTubeTV',
                'method': 'firetv_deep_link',
                'video_id': video_id,
                'is_connected': True,
            }
        except Exception as e:
            logger.error(f"tune_channel error on {self.device_name}: {e}")
            return {
                'status': 'error',
                'message': f'Failed to tune to {channel_name}',
                'device_id': self.device_id,
                'channel': channel_name,
                'error': str(e),
            }

    async def power_on(self) -> Dict[str, Any]:
        """Power on the Fire TV device (wake from sleep)

        Uses Wake-on-LAN magic packet + ADB WAKEUP command.
        """
        if not self.device_ip:
            return {'status': 'error', 'message': f'No IP configured for {self.device_name}',
                    'device_id': self.device_id}

        try:
            # Step 1: Send Wake-on-LAN packet (works even when sleeping)
            mac = FIRE_TV_MAC_ADDRESSES.get(self.device_ip)
            if mac:
                try:
                    _send_wol(mac)
                    logger.info(f"Sent WoL to {self.device_name} ({mac})")
                except Exception as e:
                    logger.warning(f"WoL failed for {self.device_name}: {e}")

            # Step 2: Wait for device to wake up
            await asyncio.sleep(3)

            # Step 3: Try ADB WAKEUP command
            try:
                await self._run_cmd('input keyevent KEYCODE_WAKEUP')
                logger.info(f"Sent ADB WAKEUP to {self.device_name}")
                return {
                    'status': 'success',
                    'message': f'{self.device_name} is now on',
                    'device_id': self.device_id,
                    'is_connected': True
                }
            except Exception as e:
                logger.warning(f"ADB WAKEUP failed for {self.device_name}: {e}")

            # WoL was sent, report success even if ADB didn't connect yet
            if mac:
                return {
                    'status': 'success',
                    'message': f'{self.device_name} - Wake-on-LAN sent',
                    'device_id': self.device_id,
                    'is_connected': False
                }

            return {'status': 'error', 'message': f'Cannot wake {self.device_name}',
                    'device_id': self.device_id}

        except Exception as e:
            logger.error(f"Failed to power on {self.device_name}: {e}")
            return {'status': 'error', 'message': f'Failed to power on {self.device_name}',
                    'device_id': self.device_id, 'error': str(e)}

    async def _wake_before_command(self):
        """Send Wake-on-LAN to ensure device is responsive before ADB commands.

        Fire TVs go into a deep sleep after idle time and won't respond to ADB
        until woken up. This sends a WoL packet and waits for the device to
        become reachable.
        """
        mac = FIRE_TV_MAC_ADDRESSES.get(self.device_ip)
        if mac:
            try:
                _send_wol(mac)
                logger.info(f"Pre-command WoL sent to {self.device_name} ({mac})")
                await asyncio.sleep(3)  # Give device time to wake up
            except Exception as e:
                logger.warning(f"Pre-command WoL failed for {self.device_name}: {e}")

    async def power_off(self) -> Dict[str, Any]:
        """Power off the Fire TV device (put into sleep/standby)"""
        if not self.device_ip:
            return {'status': 'error', 'message': f'No IP configured for {self.device_name}',
                    'device_id': self.device_id}

        try:
            # Wake device first so ADB can connect
            await self._wake_before_command()
            await self._run_cmd('input keyevent KEYCODE_SLEEP')
            logger.info(f"Sent SLEEP to {self.device_name}")
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
                'message': f'Cannot connect to {self.device_name} at {self.device_ip}. '
                           f'Enable ADB debugging on the Fire TV.',
                'device_id': self.device_id,
                'error': str(e)
            }

    async def set_volume(self, level: int) -> Dict[str, Any]:
        """Set volume level (0-100)"""
        if level < 0 or level > 100:
            return {'status': 'error', 'message': 'Volume must be between 0-100'}
        if not self.device_ip:
            return {'status': 'error', 'message': f'No IP configured for {self.device_name}',
                    'device_id': self.device_id}
        try:
            fire_tv_level = max(0, min(15, int(level / 100 * 15)))
            await self._run_cmd(f'media volume --show {fire_tv_level}')
            return {
                'status': 'success', 'message': f'Volume set to {level}% on {self.device_name}',
                'device_id': self.device_id, 'volume': level, 'is_connected': True
            }
        except Exception as e:
            logger.error(f"Failed to set volume on {self.device_name}: {e}")
            return {'status': 'error', 'message': f'Failed to set volume',
                    'device_id': self.device_id, 'error': str(e)}

    async def get_status(self) -> Dict[str, Any]:
        """Get current Fire TV status"""
        base = {
            'status': 'success', 'device_id': self.device_id,
            'device_name': self.device_name, 'device_type': self.device_type,
            'device_ip': self.device_ip
        }
        if not self.device_ip:
            base['is_connected'] = False
            return base
        try:
            result = await self._run_cmd('dumpsys window | grep mCurrentFocus')
            current_app = None
            if result and 'mCurrentFocus=' in result:
                parts = result.split('mCurrentFocus=')
                if len(parts) > 1:
                    app_str = parts[1].split('/')[0].strip()
                    current_app = app_str.split()[-1] if ' ' in app_str else app_str
            base.update({'power_state': 'on', 'volume': 50,
                        'current_app': current_app, 'is_connected': True})
        except Exception:
            base['is_connected'] = False
        return base

    async def reset_channel(self, channel: int) -> Dict[str, Any]:
        """Reset Fire TV to antenna input

        Switches the Toshiba Fire TV back to antenna input.
        The TV remembers its last antenna channel, so the user only needs
        to manually set the channel once via the physical remote.

        Navigation sequence for Toshiba Fire TV:
        1. HOME - go to home screen
        2. Pause - let home screen load
        3. LEFT x3 - navigate to Inputs section
        4. ENTER - open Inputs
        5. DOWN + ENTER - select Antenna input
        """
        if not self.device_ip:
            return {'status': 'error', 'message': f'No IP configured for {self.device_name}',
                    'device_id': self.device_id}

        try:
            logger.info(f"Resetting {self.device_name} to antenna input (channel {channel})")

            # Wake device first so ADB can connect (TVs sleep after idle)
            await self._wake_before_command()

            # Build command sequence for Toshiba Fire TV menu navigation
            # Hit HOME 3 times to wake screen and ensure we're on home screen
            commands = [
                ('input keyevent 3', 1.0),         # HOME - wake/dismiss any overlay
                ('input keyevent 3', 1.0),         # HOME - ensure home screen
                ('input keyevent 3', 2.0),         # HOME - settle on home screen
                ('input keyevent 21', 0.5),         # LEFT
                ('input keyevent 21', 0.5),         # LEFT
                ('input keyevent 21', 0.5),         # LEFT
                ('input keyevent 66', 1.0),         # ENTER - open Inputs
                ('input keyevent 20', 0.5),         # DOWN - to Antenna
                ('input keyevent 66', 1.0),         # ENTER - select Antenna
            ]

            await self._run_cmds(commands)

            logger.info(f"Reset {self.device_name} to antenna input")
            return {
                'status': 'success',
                'message': f'Reset {self.device_name} to antenna input (ch {channel})',
                'device_id': self.device_id,
                'device_name': self.device_name,
                'channel': channel,
                'is_connected': True
            }

        except Exception as e:
            logger.error(f"Failed to reset channel on {self.device_name}: {e}")
            return {
                'status': 'error',
                'message': f'Failed to reset channel on {self.device_name}',
                'device_id': self.device_id,
                'error': str(e)
            }
