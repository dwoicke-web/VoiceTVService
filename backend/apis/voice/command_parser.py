"""
Command parser - Parse voice commands and extract intent
Uses simple NLP patterns to understand user intent
"""

import re
from typing import Dict, Any, Optional, List
from enum import Enum


class CommandIntent(Enum):
    """Recognized command intents"""
    PLAY_CONTENT = "play_content"
    SEARCH_CONTENT = "search"
    CONTROL_VOLUME = "control_volume"
    CONTROL_POWER = "control_power"
    GET_INFO = "get_info"
    UNKNOWN = "unknown"


class CommandParser:
    """Parses natural language commands and extracts structured intent"""

    def __init__(self):
        """Initialize command parser"""
        self.tv_names = [
            'big screen', 'upper left', 'upper right',
            'lower left', 'lower right',
            'center', 'living room'
        ]

        self.streaming_services = [
            'youtube tv', 'youtube', 'peacock', 'espn+', 'espn plus',
            'prime video', 'hbo max', 'fandango', 'vudu', 'justwatch'
        ]

        self.play_keywords = [
            'play', 'put', 'watch', 'launch', 'open', 'start', 'show'
        ]

        self.search_keywords = [
            'find', 'search', 'look for', 'what is', 'where is'
        ]

        self.volume_keywords = [
            'volume', 'sound', 'louder', 'quieter'
        ]

        self.power_keywords = [
            'on', 'off', 'turn', 'power'
        ]

    def parse_command(self, transcript: str) -> Dict[str, Any]:
        """
        Parse a voice command transcript

        Args:
            transcript: The transcribed voice command

        Returns:
            Dictionary with parsed command structure
        """
        text = transcript.lower().strip()

        # Determine intent
        intent = self._determine_intent(text)

        # Extract parameters based on intent
        if intent == CommandIntent.PLAY_CONTENT:
            return self._parse_play_command(text)
        elif intent == CommandIntent.SEARCH_CONTENT:
            return self._parse_search_command(text)
        elif intent == CommandIntent.CONTROL_VOLUME:
            return self._parse_volume_command(text)
        elif intent == CommandIntent.CONTROL_POWER:
            return self._parse_power_command(text)
        else:
            return {
                'status': 'error',
                'message': f'Could not understand: {transcript}',
                'intent': CommandIntent.UNKNOWN.value,
                'transcript': transcript
            }

    def _determine_intent(self, text: str) -> CommandIntent:
        """Determine the intent of a command"""
        if any(keyword in text for keyword in self.play_keywords):
            return CommandIntent.PLAY_CONTENT
        elif any(keyword in text for keyword in self.search_keywords):
            return CommandIntent.SEARCH_CONTENT
        elif any(keyword in text for keyword in self.volume_keywords):
            return CommandIntent.CONTROL_VOLUME
        elif any(keyword in text for keyword in self.power_keywords):
            return CommandIntent.CONTROL_POWER
        else:
            return CommandIntent.UNKNOWN

    def _parse_play_command(self, text: str) -> Dict[str, Any]:
        """Parse a play/launch command"""
        result = {
            'status': 'success',
            'intent': CommandIntent.PLAY_CONTENT.value,
            'content_name': None,
            'tv_id': None,
            'service': None
        }

        # Extract content name (usually between "play" and "on")
        content_match = re.search(r'(?:play|put|watch|launch|open|start|show)\s+(.+?)(?:\s+on\s+|\s+at\s+|$)', text)
        if content_match:
            content = content_match.group(1).strip()
            # Remove extra words
            content = re.sub(r'\s+(on|at|the)\s+', ' ', content)
            result['content_name'] = content

        # Extract TV name
        for tv_name in self.tv_names:
            if tv_name in text:
                result['tv_id'] = tv_name.replace(' ', '_')
                break

        # Try to match streaming service
        for service in self.streaming_services:
            if service in text:
                result['service'] = service.replace(' plus', '+').title()
                break

        return result

    def _parse_search_command(self, text: str) -> Dict[str, Any]:
        """Parse a search command"""
        result = {
            'status': 'success',
            'intent': CommandIntent.SEARCH_CONTENT.value,
            'query': None
        }

        # Extract search query
        search_match = re.search(r'(?:find|search|look for|where is|what is)\s+(.+?)(?:\s+on\s+|\s+at\s+|$)', text)
        if search_match:
            result['query'] = search_match.group(1).strip()

        return result

    def _parse_volume_command(self, text: str) -> Dict[str, Any]:
        """Parse a volume control command"""
        result = {
            'status': 'success',
            'intent': CommandIntent.CONTROL_VOLUME.value,
            'level': None,
            'tv_id': None
        }

        # Extract volume level
        if 'louder' in text or 'up' in text:
            result['action'] = 'increase'
        elif 'quieter' in text or 'down' in text:
            result['action'] = 'decrease'
        elif 'mute' in text:
            result['action'] = 'mute'
        elif 'unmute' in text:
            result['action'] = 'unmute'

        # Look for specific level
        level_match = re.search(r'(\d+)\s*(?:percent|%)?', text)
        if level_match:
            level = int(level_match.group(1))
            result['level'] = min(100, max(0, level))

        # Extract TV name
        for tv_name in self.tv_names:
            if tv_name in text:
                result['tv_id'] = tv_name.replace(' ', '_')
                break

        return result

    def _parse_power_command(self, text: str) -> Dict[str, Any]:
        """Parse a power control command"""
        result = {
            'status': 'success',
            'intent': CommandIntent.CONTROL_POWER.value,
            'action': None,
            'tv_id': None
        }

        # Determine action
        if 'off' in text or 'turn off' in text:
            result['action'] = 'off'
        elif 'on' in text or 'turn on' in text:
            result['action'] = 'on'

        # Extract TV name
        for tv_name in self.tv_names:
            if tv_name in text:
                result['tv_id'] = tv_name.replace(' ', '_')
                break

        return result


# Global command parser
_command_parser = None


def get_command_parser() -> CommandParser:
    """Get or create the global command parser"""
    global _command_parser
    if _command_parser is None:
        _command_parser = CommandParser()
    return _command_parser
