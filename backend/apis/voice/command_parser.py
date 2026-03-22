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
    WATCH_GAME = "watch_game"
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

        # NHL teams (32 teams)
        self.nhl_teams = {
            'penguins': ('Penguins', 'nhl'), 'pittsburgh penguins': ('Penguins', 'nhl'), 'pens': ('Penguins', 'nhl'),
            'flyers': ('Flyers', 'nhl'), 'philadelphia flyers': ('Flyers', 'nhl'),
            'bruins': ('Bruins', 'nhl'), 'boston bruins': ('Bruins', 'nhl'),
            'rangers': ('Rangers', 'nhl'), 'new york rangers': ('Rangers', 'nhl'),
            'islanders': ('Islanders', 'nhl'), 'new york islanders': ('Islanders', 'nhl'),
            'devils': ('Devils', 'nhl'), 'new jersey devils': ('Devils', 'nhl'),
            'capitals': ('Capitals', 'nhl'), 'washington capitals': ('Capitals', 'nhl'), 'caps': ('Capitals', 'nhl'),
            'hurricanes': ('Hurricanes', 'nhl'), 'carolina hurricanes': ('Hurricanes', 'nhl'), 'canes': ('Hurricanes', 'nhl'),
            'panthers': ('Panthers', 'nhl'), 'florida panthers': ('Panthers', 'nhl'),
            'lightning': ('Lightning', 'nhl'), 'tampa bay lightning': ('Lightning', 'nhl'), 'bolts': ('Lightning', 'nhl'),
            'red wings': ('Red Wings', 'nhl'), 'detroit red wings': ('Red Wings', 'nhl'),
            'blackhawks': ('Blackhawks', 'nhl'), 'chicago blackhawks': ('Blackhawks', 'nhl'), 'hawks': ('Blackhawks', 'nhl'),
            'blue jackets': ('Blue Jackets', 'nhl'), 'columbus blue jackets': ('Blue Jackets', 'nhl'),
            'predators': ('Predators', 'nhl'), 'nashville predators': ('Predators', 'nhl'), 'preds': ('Predators', 'nhl'),
            'blues': ('Blues', 'nhl'), 'st louis blues': ('Blues', 'nhl'),
            'wild': ('Wild', 'nhl'), 'minnesota wild': ('Wild', 'nhl'),
            'stars': ('Stars', 'nhl'), 'dallas stars': ('Stars', 'nhl'),
            'avalanche': ('Avalanche', 'nhl'), 'colorado avalanche': ('Avalanche', 'nhl'), 'avs': ('Avalanche', 'nhl'),
            'jets': ('Jets', 'nhl'), 'winnipeg jets': ('Jets', 'nhl'),
            'flames': ('Flames', 'nhl'), 'calgary flames': ('Flames', 'nhl'),
            'oilers': ('Oilers', 'nhl'), 'edmonton oilers': ('Oilers', 'nhl'),
            'canucks': ('Canucks', 'nhl'), 'vancouver canucks': ('Canucks', 'nhl'),
            'kraken': ('Kraken', 'nhl'), 'seattle kraken': ('Kraken', 'nhl'),
            'golden knights': ('Golden Knights', 'nhl'), 'vegas golden knights': ('Golden Knights', 'nhl'), 'knights': ('Golden Knights', 'nhl'),
            'kings': ('Kings', 'nhl'), 'la kings': ('Kings', 'nhl'), 'los angeles kings': ('Kings', 'nhl'),
            'ducks': ('Ducks', 'nhl'), 'anaheim ducks': ('Ducks', 'nhl'),
            'sharks': ('Sharks', 'nhl'), 'san jose sharks': ('Sharks', 'nhl'),
            'sabres': ('Sabres', 'nhl'), 'buffalo sabres': ('Sabres', 'nhl'),
            'senators': ('Senators', 'nhl'), 'ottawa senators': ('Senators', 'nhl'), 'sens': ('Senators', 'nhl'),
            'maple leafs': ('Maple Leafs', 'nhl'), 'toronto maple leafs': ('Maple Leafs', 'nhl'), 'leafs': ('Maple Leafs', 'nhl'),
            'canadiens': ('Canadiens', 'nhl'), 'montreal canadiens': ('Canadiens', 'nhl'), 'habs': ('Canadiens', 'nhl'),
            'utah hockey club': ('Utah Hockey Club', 'nhl'), 'utah': ('Utah Hockey Club', 'nhl'),
        }

        # NBA teams (30 teams)
        self.nba_teams = {
            'lakers': ('Lakers', 'nba'), 'la lakers': ('Lakers', 'nba'), 'los angeles lakers': ('Lakers', 'nba'),
            'celtics': ('Celtics', 'nba'), 'boston celtics': ('Celtics', 'nba'),
            'warriors': ('Warriors', 'nba'), 'golden state warriors': ('Warriors', 'nba'),
            '76ers': ('76ers', 'nba'), 'sixers': ('76ers', 'nba'), 'philadelphia 76ers': ('76ers', 'nba'),
            'nets': ('Nets', 'nba'), 'brooklyn nets': ('Nets', 'nba'),
            'knicks': ('Knicks', 'nba'), 'new york knicks': ('Knicks', 'nba'),
            'bucks': ('Bucks', 'nba'), 'milwaukee bucks': ('Bucks', 'nba'),
            'heat': ('Heat', 'nba'), 'miami heat': ('Heat', 'nba'),
            'bulls': ('Bulls', 'nba'), 'chicago bulls': ('Bulls', 'nba'),
            'cavaliers': ('Cavaliers', 'nba'), 'cleveland cavaliers': ('Cavaliers', 'nba'), 'cavs': ('Cavaliers', 'nba'),
            'raptors': ('Raptors', 'nba'), 'toronto raptors': ('Raptors', 'nba'),
            'pacers': ('Pacers', 'nba'), 'indiana pacers': ('Pacers', 'nba'),
            'hawks': ('Hawks', 'nba'), 'atlanta hawks': ('Hawks', 'nba'),
            'hornets': ('Hornets', 'nba'), 'charlotte hornets': ('Hornets', 'nba'),
            'wizards': ('Wizards', 'nba'), 'washington wizards': ('Wizards', 'nba'),
            'magic': ('Magic', 'nba'), 'orlando magic': ('Magic', 'nba'),
            'pistons': ('Pistons', 'nba'), 'detroit pistons': ('Pistons', 'nba'),
            'spurs': ('Spurs', 'nba'), 'san antonio spurs': ('Spurs', 'nba'),
            'mavericks': ('Mavericks', 'nba'), 'dallas mavericks': ('Mavericks', 'nba'), 'mavs': ('Mavericks', 'nba'),
            'rockets': ('Rockets', 'nba'), 'houston rockets': ('Rockets', 'nba'),
            'grizzlies': ('Grizzlies', 'nba'), 'memphis grizzlies': ('Grizzlies', 'nba'),
            'pelicans': ('Pelicans', 'nba'), 'new orleans pelicans': ('Pelicans', 'nba'),
            'timberwolves': ('Timberwolves', 'nba'), 'minnesota timberwolves': ('Timberwolves', 'nba'), 'wolves': ('Timberwolves', 'nba'),
            'nuggets': ('Nuggets', 'nba'), 'denver nuggets': ('Nuggets', 'nba'),
            'trail blazers': ('Trail Blazers', 'nba'), 'portland trail blazers': ('Trail Blazers', 'nba'), 'blazers': ('Trail Blazers', 'nba'),
            'thunder': ('Thunder', 'nba'), 'oklahoma city thunder': ('Thunder', 'nba'), 'okc': ('Thunder', 'nba'),
            'jazz': ('Jazz', 'nba'), 'utah jazz': ('Jazz', 'nba'),
            'suns': ('Suns', 'nba'), 'phoenix suns': ('Suns', 'nba'),
            'clippers': ('Clippers', 'nba'), 'la clippers': ('Clippers', 'nba'), 'los angeles clippers': ('Clippers', 'nba'),
            'kings': ('Kings', 'nba'), 'sacramento kings': ('Kings', 'nba'),
        }

        # NFL teams (32 teams)
        self.nfl_teams = {
            'steelers': ('Steelers', 'nfl'), 'pittsburgh steelers': ('Steelers', 'nfl'),
            'eagles': ('Eagles', 'nfl'), 'philadelphia eagles': ('Eagles', 'nfl'),
            'chiefs': ('Chiefs', 'nfl'), 'kansas city chiefs': ('Chiefs', 'nfl'),
            'cowboys': ('Cowboys', 'nfl'), 'dallas cowboys': ('Cowboys', 'nfl'),
            'packers': ('Packers', 'nfl'), 'green bay packers': ('Packers', 'nfl'),
            'patriots': ('Patriots', 'nfl'), 'new england patriots': ('Patriots', 'nfl'), 'pats': ('Patriots', 'nfl'),
            'bills': ('Bills', 'nfl'), 'buffalo bills': ('Bills', 'nfl'),
            'ravens': ('Ravens', 'nfl'), 'baltimore ravens': ('Ravens', 'nfl'),
            'bengals': ('Bengals', 'nfl'), 'cincinnati bengals': ('Bengals', 'nfl'),
            'browns': ('Browns', 'nfl'), 'cleveland browns': ('Browns', 'nfl'),
            'dolphins': ('Dolphins', 'nfl'), 'miami dolphins': ('Dolphins', 'nfl'),
            'jets': ('Jets', 'nfl'), 'new york jets': ('Jets', 'nfl'),
            'giants': ('Giants', 'nfl'), 'new york giants': ('Giants', 'nfl'),
            'texans': ('Texans', 'nfl'), 'houston texans': ('Texans', 'nfl'),
            'colts': ('Colts', 'nfl'), 'indianapolis colts': ('Colts', 'nfl'),
            'jaguars': ('Jaguars', 'nfl'), 'jacksonville jaguars': ('Jaguars', 'nfl'), 'jags': ('Jaguars', 'nfl'),
            'titans': ('Titans', 'nfl'), 'tennessee titans': ('Titans', 'nfl'),
            'broncos': ('Broncos', 'nfl'), 'denver broncos': ('Broncos', 'nfl'),
            'chargers': ('Chargers', 'nfl'), 'los angeles chargers': ('Chargers', 'nfl'), 'la chargers': ('Chargers', 'nfl'),
            'raiders': ('Raiders', 'nfl'), 'las vegas raiders': ('Raiders', 'nfl'),
            'seahawks': ('Seahawks', 'nfl'), 'seattle seahawks': ('Seahawks', 'nfl'),
            '49ers': ('49ers', 'nfl'), 'san francisco 49ers': ('49ers', 'nfl'), 'niners': ('49ers', 'nfl'),
            'rams': ('Rams', 'nfl'), 'los angeles rams': ('Rams', 'nfl'), 'la rams': ('Rams', 'nfl'),
            'cardinals': ('Cardinals', 'nfl'), 'arizona cardinals': ('Cardinals', 'nfl'),
            'falcons': ('Falcons', 'nfl'), 'atlanta falcons': ('Falcons', 'nfl'),
            'saints': ('Saints', 'nfl'), 'new orleans saints': ('Saints', 'nfl'),
            'panthers': ('Panthers', 'nfl'), 'carolina panthers': ('Panthers', 'nfl'),
            'buccaneers': ('Buccaneers', 'nfl'), 'tampa bay buccaneers': ('Buccaneers', 'nfl'), 'bucs': ('Buccaneers', 'nfl'),
            'bears': ('Bears', 'nfl'), 'chicago bears': ('Bears', 'nfl'),
            'lions': ('Lions', 'nfl'), 'detroit lions': ('Lions', 'nfl'),
            'vikings': ('Vikings', 'nfl'), 'minnesota vikings': ('Vikings', 'nfl'),
            'commanders': ('Commanders', 'nfl'), 'washington commanders': ('Commanders', 'nfl'),
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

        # 3.5. Watch a specific sports game
        if self._is_watch_game(text):
            return self._parse_watch_game(text)

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

    def _is_watch_game(self, text: str) -> bool:
        """Check if this is a request to watch a sports game"""
        team_info = self._extract_sports_team(text)
        if not team_info:
            return False
        # Must have a play-type verb
        has_watch = any(k in text for k in ['watch', 'put on', 'show', 'play'])
        # Or mention "game"
        has_game = 'game' in text
        return has_watch or has_game

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

    def _parse_watch_game(self, text: str) -> Dict[str, Any]:
        team_name, sport = self._extract_sports_team(text)
        tv_id = self._extract_tv(text)
        return {
            'status': 'success',
            'intent': CommandIntent.WATCH_GAME.value,
            'team': team_name,
            'sport': sport,
            'tv_id': tv_id,
            'voice_response': f"Finding the {team_name} game..."
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

    def _extract_sports_team(self, text: str):
        """Extract any sports team (NHL, NBA, NFL, MLB) from text.
        Returns (team_name, sport) tuple or None.
        """
        # Check all sport dicts, longest match first
        all_teams = {}
        for phrase, val in self.nhl_teams.items():
            all_teams[phrase] = val
        for phrase, val in self.nba_teams.items():
            all_teams[phrase] = val
        for phrase, val in self.nfl_teams.items():
            all_teams[phrase] = val
        for phrase, val in self.mlb_teams.items():
            all_teams[phrase] = (val, 'mlb')

        for phrase in sorted(all_teams.keys(), key=len, reverse=True):
            if phrase in text:
                result = all_teams[phrase]
                if isinstance(result, tuple):
                    return result  # (team_name, sport)
                return (result, 'unknown')
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
