"""
Command parser - Parse voice commands and extract intent
Supports: play content, search, power control, reset antenna, launch apps
"""

import re
from typing import Dict, Any
from enum import Enum


class CommandIntent(Enum):
    PLAY_CONTENT = "play_content"
    SEARCH_CONTENT = "search"
    CONTROL_VOLUME = "control_volume"
    CONTROL_POWER = "control_power"
    RESET_ANTENNA = "reset_antenna"
    LAUNCH_APP = "launch_app"
    TUNE_CHANNEL = "tune_channel"
    GET_INFO = "get_info"
    UNKNOWN = "unknown"


class CommandParser:
    """Parses natural language voice commands"""

    def __init__(self):
        # TV name mappings (voice phrase -> device ID)
        self.tv_map = {
            'upper left': 'upper_left',
            'top left': 'upper_left',
            'upper right': 'upper_right',
            'top right': 'upper_right',
            'lower left': 'lower_left',
            'bottom left': 'lower_left',
            'lower right': 'lower_right',
            'bottom right': 'lower_right',
            'all': 'all',
            'everything': 'all',
            'all tvs': 'all',
            'all the tvs': 'all',
        }

        # YouTube TV channel name mappings (voice phrase -> channel name for search)
        self.channel_map = {
            'espn': 'ESPN',
            'espn2': 'ESPN2',
            'espn 2': 'ESPN2',
            'espn two': 'ESPN2',
            'espn u': 'ESPNU',
            'espn news': 'ESPNews',
            'cbs': 'CBS',
            'nbc': 'NBC',
            'abc': 'ABC',
            'fox': 'FOX',
            'fox news': 'Fox News',
            'fox sports': 'FS1',
            'fox sports 1': 'FS1',
            'fox sports 2': 'FS2',
            'fs1': 'FS1',
            'fs2': 'FS2',
            'cnn': 'CNN',
            'msnbc': 'MSNBC',
            'tbs': 'TBS',
            'tnt': 'TNT',
            'usa': 'USA Network',
            'usa network': 'USA Network',
            'bravo': 'Bravo',
            'hgtv': 'HGTV',
            'food network': 'Food Network',
            'discovery': 'Discovery',
            'history': 'History',
            'history channel': 'History',
            'comedy central': 'Comedy Central',
            'mtv': 'MTV',
            'bet': 'BET',
            'nickelodeon': 'Nickelodeon',
            'nick': 'Nickelodeon',
            'cartoon network': 'Cartoon Network',
            'disney channel': 'Disney Channel',
            'disney junior': 'Disney Junior',
            'freeform': 'Freeform',
            'fx': 'FX',
            'fxx': 'FXX',
            'amc': 'AMC',
            'syfy': 'Syfy',
            'e!': 'E!',
            'tlc': 'TLC',
            'animal planet': 'Animal Planet',
            'national geographic': 'National Geographic',
            'nat geo': 'National Geographic',
            'pbs': 'PBS',
            'the cw': 'The CW',
            'cw': 'The CW',
            'nfl network': 'NFL Network',
            'mlb network': 'MLB Network',
            'nba tv': 'NBA TV',
            'golf channel': 'Golf Channel',
            'sec network': 'SEC Network',
            'big ten network': 'Big Ten Network',
            'acc network': 'ACC Network',
            'paramount network': 'Paramount Network',
            'hallmark': 'Hallmark Channel',
            'hallmark channel': 'Hallmark Channel',
            'lifetime': 'Lifetime',
            'a&e': 'A&E',
            'oxygen': 'Oxygen',
            'travel channel': 'Travel Channel',
            'newsmax': 'Newsmax',
            'local news': 'Local News',
        }

        # MLB team names (30 teams) for auto-routing to MLB app
        self.mlb_teams = {
            'yankees': 'Yankees', 'new york yankees': 'Yankees',
            'mets': 'Mets', 'new york mets': 'Mets',
            'red sox': 'Red Sox', 'boston red sox': 'Red Sox',
            'dodgers': 'Dodgers', 'los angeles dodgers': 'Dodgers', 'la dodgers': 'Dodgers',
            'cubs': 'Cubs', 'chicago cubs': 'Cubs',
            'white sox': 'White Sox', 'chicago white sox': 'White Sox',
            'cardinals': 'Cardinals', 'st louis cardinals': 'Cardinals', 'saint louis cardinals': 'Cardinals',
            'giants': 'Giants', 'san francisco giants': 'Giants', 'sf giants': 'Giants',
            'braves': 'Braves', 'atlanta braves': 'Braves',
            'astros': 'Astros', 'houston astros': 'Astros',
            'phillies': 'Phillies', 'philadelphia phillies': 'Phillies',
            'padres': 'Padres', 'san diego padres': 'Padres',
            'rangers': 'Rangers', 'texas rangers': 'Rangers',
            'blue jays': 'Blue Jays', 'toronto blue jays': 'Blue Jays',
            'twins': 'Twins', 'minnesota twins': 'Twins',
            'mariners': 'Mariners', 'seattle mariners': 'Mariners',
            'guardians': 'Guardians', 'cleveland guardians': 'Guardians',
            'rays': 'Rays', 'tampa bay rays': 'Rays',
            'orioles': 'Orioles', 'baltimore orioles': 'Orioles',
            'brewers': 'Brewers', 'milwaukee brewers': 'Brewers',
            'diamondbacks': 'Diamondbacks', 'arizona diamondbacks': 'Diamondbacks', 'd-backs': 'Diamondbacks',
            'reds': 'Reds', 'cincinnati reds': 'Reds',
            'royals': 'Royals', 'kansas city royals': 'Royals',
            'pirates': 'Pirates', 'pittsburgh pirates': 'Pirates',
            'tigers': 'Tigers', 'detroit tigers': 'Tigers',
            'angels': 'Angels', 'los angeles angels': 'Angels', 'la angels': 'Angels',
            'athletics': 'Athletics', 'oakland athletics': 'Athletics', "a's": 'Athletics', 'as': 'Athletics',
            'rockies': 'Rockies', 'colorado rockies': 'Rockies',
            'marlins': 'Marlins', 'miami marlins': 'Marlins',
            'nationals': 'Nationals', 'washington nationals': 'Nationals',
        }

        # Streaming service name mappings
        self.service_map = {
            'youtube tv': 'YouTubeTV',
            'youtube': 'YouTube',
            'netflix': 'Netflix',
            'espn': 'ESPN',
            'espn plus': 'ESPN+',
            'prime video': 'Prime Video',
            'amazon prime': 'Prime Video',
            'hbo max': 'HBO Max',
            'hbo': 'HBO Max',
            'max': 'HBO Max',
            'mlb': 'MLB',
            'baseball': 'MLB',
            'disney plus': 'Disney+',
            'disney': 'Disney+',
            'hulu': 'Hulu',
            'peacock': 'Peacock',
            'vudu': 'Vudu',
        }

    def parse_command(self, transcript: str) -> Dict[str, Any]:
        """Parse a voice command transcript into structured intent"""
        text = transcript.lower().strip()

        # Check intents in priority order
        # 1. Power all on/off
        if self._is_power_all(text):
            return self._parse_power_all(text)

        # 2. Reset antenna
        if self._is_reset_antenna(text):
            return self._parse_reset_antenna(text)

        # 3. Tune to a channel on YouTube TV
        if self._is_tune_channel(text):
            return self._parse_tune_channel(text)

        # 4. Launch specific app
        if self._is_launch_app(text):
            return self._parse_launch_app(text)

        # 5. Power single TV
        if self._is_power_command(text):
            return self._parse_power_command(text)

        # 6. Play content
        if self._is_play_command(text):
            return self._parse_play_command(text)

        # 7. Search
        if self._is_search_command(text):
            return self._parse_search_command(text)

        # 8. Volume
        if self._is_volume_command(text):
            return self._parse_volume_command(text)

        return {
            'status': 'error',
            'message': f'Could not understand: {transcript}',
            'intent': CommandIntent.UNKNOWN.value,
            'transcript': transcript
        }

    # --- Intent detection ---

    def _is_power_all(self, text: str) -> bool:
        # Skip if this looks like a launch/open/start command
        if any(k in text for k in ['launch', 'open', 'start', 'tune', 'switch to', 'put on']):
            return False
        patterns = [
            r'(?:turn|power)\s+(?:on|off)\s+(?:all|everything)',
            r'(?:all|everything)\s+(?:on|off)',
            r'(?:turn|power)\s+(?:all|everything)\s+(?:on|off)',
            r'\b(?:tvs?|televisions?)\s+(?:on|off)',
            r'(?:turn|power)\s+(?:on|off)\s+(?:the\s+)?(?:tvs?|televisions?)',
        ]
        return any(re.search(p, text) for p in patterns)

    def _is_reset_antenna(self, text: str) -> bool:
        # Must mention 'reset' or 'antenna' explicitly - 'channel' alone is too generic
        has_reset = 'reset' in text or 'antenna' in text
        has_tuner = 'tuner' in text or 'broadcast' in text
        return has_reset or has_tuner

    def _is_tune_channel(self, text: str) -> bool:
        # Strong tune verbs always mean channel tuning when a channel is found
        strong_tune = any(k in text for k in [
            'tune to', 'tune in', 'tune ', 'change to', 'turn to', 'change channel',
        ])
        has_channel = self._extract_channel(text) is not None

        if strong_tune and has_channel:
            return True

        # Weaker verbs (watch, put on, switch to, go to) - prefer channel if no service match,
        # or if channel is found and it's NOT also an app name (like "Netflix")
        weak_tune = any(k in text for k in [
            'switch to', 'put on', 'go to', 'watch', 'turn on',
        ])
        if weak_tune and has_channel:
            # Check if the matched channel name is ALSO a streaming app
            channel = self._extract_channel(text)
            service = self._extract_service(text)
            # If the channel and service point to the same thing (e.g. ESPN),
            # prefer channel for these verbs unless "launch"/"open"/"start" is also present
            has_launch = any(k in text for k in ['launch', 'open', 'start'])
            if not has_launch:
                return True

        return False

    def _is_launch_app(self, text: str) -> bool:
        # Check if text mentions a known service with launch intent
        has_launch = any(k in text for k in ['launch', 'open', 'start', 'put on', 'switch to'])
        has_service = any(svc in text for svc in self.service_map)
        return has_launch and has_service

    def _is_power_command(self, text: str) -> bool:
        return bool(re.search(r'(?:turn|power)\s+(?:on|off)', text))

    def _is_play_command(self, text: str) -> bool:
        return any(k in text for k in ['play', 'put', 'watch', 'show me'])

    def _is_search_command(self, text: str) -> bool:
        return any(k in text for k in ['find', 'search', 'look for', 'what is', 'where is', 'where can'])

    def _is_volume_command(self, text: str) -> bool:
        return any(k in text for k in ['volume', 'louder', 'quieter', 'mute', 'unmute'])

    # --- Parsers ---

    def _parse_power_all(self, text: str) -> Dict[str, Any]:
        action = 'off' if 'off' in text else 'on'
        return {
            'status': 'success',
            'intent': CommandIntent.CONTROL_POWER.value,
            'action': action,
            'tv_id': 'all',
            'voice_response': f"Turning {'on' if action == 'on' else 'off'} all TVs"
        }

    def _parse_reset_antenna(self, text: str) -> Dict[str, Any]:
        tv_id = self._extract_tv(text)
        return {
            'status': 'success',
            'intent': CommandIntent.RESET_ANTENNA.value,
            'tv_id': tv_id or 'all',
            'voice_response': f"Resetting {'all TVs' if not tv_id or tv_id == 'all' else tv_id.replace('_', ' ')} to antenna"
        }

    def _parse_tune_channel(self, text: str) -> Dict[str, Any]:
        channel = self._extract_channel(text)
        tv_id = self._extract_tv(text)
        return {
            'status': 'success',
            'intent': CommandIntent.TUNE_CHANNEL.value,
            'channel': channel,
            'tv_id': tv_id,
            'voice_response': f"Tuning to {channel}" + (f" on {tv_id.replace('_', ' ')}" if tv_id else "")
        }

    def _parse_launch_app(self, text: str) -> Dict[str, Any]:
        service = self._extract_service(text)
        tv_id = self._extract_tv(text)
        return {
            'status': 'success',
            'intent': CommandIntent.LAUNCH_APP.value,
            'service': service,
            'tv_id': tv_id,
            'voice_response': f"Launching {service}" + (f" on {tv_id.replace('_', ' ')}" if tv_id else "")
        }

    def _parse_power_command(self, text: str) -> Dict[str, Any]:
        action = 'off' if 'off' in text else 'on'
        tv_id = self._extract_tv(text)
        return {
            'status': 'success',
            'intent': CommandIntent.CONTROL_POWER.value,
            'action': action,
            'tv_id': tv_id,
            'voice_response': f"Turning {action} {tv_id.replace('_', ' ') if tv_id else 'TV'}"
        }

    def _parse_play_command(self, text: str) -> Dict[str, Any]:
        # Extract content name between play verb and "on [TV]"
        content_match = re.search(
            r'(?:play|put|watch|show me)\s+(.+?)(?:\s+on\s+(?:the\s+)?(?:' +
            '|'.join(self.tv_map.keys()) + r')|\s*$)', text
        )
        content_name = content_match.group(1).strip() if content_match else text
        # Clean up
        content_name = re.sub(r'^(?:the|a|an)\s+', '', content_name)

        tv_id = self._extract_tv(text)
        service = self._extract_service(text)

        # Auto-detect MLB team → route to MLB app
        mlb_team = self._extract_mlb_team(text)
        if mlb_team and not service:
            service = 'MLB'
            content_name = mlb_team

        return {
            'status': 'success',
            'intent': CommandIntent.PLAY_CONTENT.value,
            'content_name': content_name,
            'tv_id': tv_id,
            'service': service,
            'mlb_team': mlb_team,
            'voice_response': f"Playing {content_name}" + (" on MLB" if mlb_team else "")
        }

    def _parse_search_command(self, text: str) -> Dict[str, Any]:
        search_match = re.search(
            r'(?:find|search|search for|look for|where is|where can i (?:find|watch))\s+(.+?)$', text
        )
        query = search_match.group(1).strip() if search_match else text
        return {
            'status': 'success',
            'intent': CommandIntent.SEARCH_CONTENT.value,
            'query': query,
            'voice_response': f"Searching for {query}"
        }

    def _parse_volume_command(self, text: str) -> Dict[str, Any]:
        result = {
            'status': 'success',
            'intent': CommandIntent.CONTROL_VOLUME.value,
            'tv_id': self._extract_tv(text),
            'level': None,
            'action': None,
        }

        if 'louder' in text or 'up' in text:
            result['action'] = 'increase'
        elif 'quieter' in text or 'down' in text:
            result['action'] = 'decrease'
        elif 'mute' in text:
            result['action'] = 'mute'

        level_match = re.search(r'(\d+)\s*(?:percent|%)?', text)
        if level_match:
            result['level'] = min(100, max(0, int(level_match.group(1))))

        result['voice_response'] = f"Volume {'set to ' + str(result['level']) + '%' if result['level'] else result['action'] or 'adjusted'}"
        return result

    # --- Extraction helpers ---

    def _extract_tv(self, text: str) -> str:
        """Extract TV identifier from text"""
        # Check longest matches first (e.g., "upper left" before "left")
        for phrase in sorted(self.tv_map.keys(), key=len, reverse=True):
            if phrase in text:
                return self.tv_map[phrase]
        return None

    def _extract_mlb_team(self, text: str) -> str:
        """Extract MLB team name from text"""
        for phrase in sorted(self.mlb_teams.keys(), key=len, reverse=True):
            if phrase in text:
                return self.mlb_teams[phrase]
        return None

    def _extract_channel(self, text: str) -> str:
        """Extract TV channel name from text"""
        # Check longest matches first (e.g., "fox news" before "fox")
        for phrase in sorted(self.channel_map.keys(), key=len, reverse=True):
            if phrase in text:
                return self.channel_map[phrase]
        return None

    def _extract_service(self, text: str) -> str:
        """Extract streaming service name from text"""
        for phrase in sorted(self.service_map.keys(), key=len, reverse=True):
            if phrase in text:
                return self.service_map[phrase]
        return None


# Global command parser
_command_parser = None


def get_command_parser() -> CommandParser:
    global _command_parser
    if _command_parser is None:
        _command_parser = CommandParser()
    return _command_parser
