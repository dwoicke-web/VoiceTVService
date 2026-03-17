"""
Sonos speaker integration module
Real implementation using SoCo library for Sonos control and gTTS for text-to-speech.
Speaks responses through the Sonos Beam soundbar in the basement.
"""

import os
import logging
import tempfile
import threading
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

# Sonos speaker IPs discovered on the network
SONOS_DEVICES = {
    'beam': {
        'ip': '192.168.4.74',
        'name': 'Basement Beam',
        'model': 'Sonos Beam',
    },
    'left_surround': {
        'ip': '192.168.4.76',
        'name': 'Basement Left',
        'model': 'Sonos One SL',
    },
    'right_surround': {
        'ip': '192.168.4.77',
        'name': 'Basement Right',
        'model': 'Sonos One SL',
    },
}


class SonosDevice:
    """Real Sonos speaker device controlled via SoCo"""

    def __init__(self, device_id: str, device_name: str, ip_address: Optional[str] = None):
        self.device_id = device_id
        self.device_name = device_name
        self.ip_address = ip_address
        self._speaker = None

    def _get_speaker(self):
        """Get or create SoCo speaker instance"""
        if not self.ip_address:
            return None
        if self._speaker is None:
            try:
                import soco
                self._speaker = soco.SoCo(self.ip_address)
                # Test connection
                _ = self._speaker.player_name
                logger.info(f"Connected to Sonos {self.device_name} at {self.ip_address}")
            except Exception as e:
                logger.error(f"Failed to connect to Sonos {self.device_name}: {e}")
                self._speaker = None
        return self._speaker

    async def speak(self, text: str, volume: int = 40) -> Dict[str, Any]:
        """
        Play text-to-speech on the Sonos speaker using gTTS + Sonos HTTP playback.

        Generates an MP3 via Google TTS, serves it via a temporary HTTP server,
        and plays it on the Sonos speaker.
        """
        speaker = self._get_speaker()
        if not speaker:
            logger.warning(f"No Sonos speaker available for {self.device_name}, skipping TTS")
            return {
                'status': 'mock',
                'message': f'No speaker connected: "{text}"',
                'device_id': self.device_id,
                'text': text
            }

        try:
            from gtts import gTTS
            import socket
            import http.server
            import time

            # Generate TTS audio file
            tts = gTTS(text=text, lang='en', slow=False)
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                tts_path = f.name
                tts.save(tts_path)

            logger.info(f"Generated TTS audio: {tts_path}")

            # Get our IP address that Sonos can reach
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect((self.ip_address, 1400))
            our_ip = s.getsockname()[0]
            s.close()

            # Serve the file via a temporary HTTP server
            import os
            tts_dir = os.path.dirname(tts_path)
            tts_filename = os.path.basename(tts_path)

            # Find a free port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('', 0))
            port = sock.getsockname()[1]
            sock.close()

            # Start HTTP server in background thread
            class QuietHandler(http.server.SimpleHTTPRequestHandler):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, directory=tts_dir, **kwargs)
                def log_message(self, format, *args):
                    pass  # Suppress logs

            httpd = http.server.HTTPServer(('0.0.0.0', port), QuietHandler)
            server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            server_thread.start()

            tts_url = f'http://{our_ip}:{port}/{tts_filename}'
            logger.info(f"Serving TTS at {tts_url}")

            # Save current state
            try:
                current_volume = speaker.volume
                current_uri = None
                transport_info = speaker.get_current_transport_info()
                was_playing = transport_info.get('current_transport_state') == 'PLAYING'
                if was_playing:
                    media_info = speaker.get_current_media_info()
                    current_uri = media_info.get('uri', '')
            except Exception:
                current_volume = 48
                was_playing = False
                current_uri = None

            # Play TTS
            speaker.volume = volume
            speaker.play_uri(tts_url, title='TV Control')

            # Wait for playback to finish (estimate from text length)
            words = len(text.split())
            wait_time = max(2.0, words * 0.4 + 1.0)
            time.sleep(wait_time)

            # Restore volume
            speaker.volume = current_volume

            # Stop TTS playback
            try:
                speaker.stop()
            except Exception:
                pass

            # Cleanup
            def cleanup():
                time.sleep(2)
                httpd.shutdown()
                try:
                    os.unlink(tts_path)
                except Exception:
                    pass

            threading.Thread(target=cleanup, daemon=True).start()

            logger.info(f"TTS playback complete on {self.device_name}: '{text}'")
            return {
                'status': 'success',
                'message': f'Spoke on {self.device_name}',
                'device_id': self.device_id,
                'text': text
            }

        except Exception as e:
            logger.error(f"TTS failed on {self.device_name}: {e}")
            return {
                'status': 'error',
                'message': f'TTS failed: {str(e)}',
                'device_id': self.device_id,
                'text': text
            }

    async def set_volume(self, level: int) -> Dict[str, Any]:
        """Set speaker volume (0-100)"""
        if level < 0 or level > 100:
            return {'status': 'error', 'message': 'Volume must be 0-100'}

        speaker = self._get_speaker()
        if speaker:
            try:
                speaker.volume = level
                return {
                    'status': 'success',
                    'device_id': self.device_id,
                    'volume': level
                }
            except Exception as e:
                return {'status': 'error', 'message': str(e)}

        return {
            'status': 'mock',
            'message': f'No speaker connected, volume would be {level}',
            'device_id': self.device_id,
            'volume': level
        }

    async def get_status(self) -> Dict[str, Any]:
        """Get speaker status"""
        speaker = self._get_speaker()
        if speaker:
            try:
                info = speaker.get_speaker_info()
                transport = speaker.get_current_transport_info()
                return {
                    'status': 'success',
                    'device_id': self.device_id,
                    'device_name': self.device_name,
                    'ip_address': self.ip_address,
                    'model': info.get('model_name', 'unknown'),
                    'volume': speaker.volume,
                    'is_playing': transport.get('current_transport_state') == 'PLAYING',
                    'is_connected': True
                }
            except Exception as e:
                logger.warning(f"Status check failed for {self.device_name}: {e}")

        return {
            'status': 'success',
            'device_id': self.device_id,
            'device_name': self.device_name,
            'ip_address': self.ip_address,
            'is_connected': False
        }


class SonosManager:
    """Manages Sonos speaker discovery and control"""

    def __init__(self):
        self.devices: Dict[str, SonosDevice] = {}
        self._init_devices()

    def _init_devices(self):
        """Initialize known Sonos devices"""
        for device_id, info in SONOS_DEVICES.items():
            ip = os.environ.get(f'SONOS_{device_id.upper()}_IP', info['ip'])
            self.devices[device_id] = SonosDevice(
                device_id=device_id,
                device_name=info['name'],
                ip_address=ip
            )
        logger.info(f"Initialized {len(self.devices)} Sonos devices")

    def get_device(self, device_id: str) -> Optional[SonosDevice]:
        """Get a speaker device by ID"""
        return self.devices.get(device_id)

    def get_beam(self) -> Optional[SonosDevice]:
        """Get the main Beam soundbar (used for TTS feedback)"""
        return self.devices.get('beam')

    def get_all_devices(self) -> Dict[str, SonosDevice]:
        return self.devices

    async def speak(self, text: str, volume: int = 40) -> Dict[str, Any]:
        """Speak text on the Beam (main speaker)"""
        beam = self.get_beam()
        if beam:
            return await beam.speak(text, volume=volume)
        return {'status': 'error', 'message': 'No Beam speaker found'}


# Global Sonos manager
_sonos_manager = None


def get_sonos_manager() -> SonosManager:
    """Get or create the global Sonos manager"""
    global _sonos_manager
    if _sonos_manager is None:
        _sonos_manager = SonosManager()
    return _sonos_manager
