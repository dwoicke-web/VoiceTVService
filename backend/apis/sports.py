"""
ESPN Scoreboard integration - Live sports games with broadcast-to-app mapping.
Fetches live/upcoming/completed games from ESPN's public API and maps
broadcast networks to launchable Roku apps.
"""

import asyncio
import aiohttp
import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

ESPN_API_BASE = 'https://site.api.espn.com/apis/site/v2/sports'

# Major leagues to fetch
LEAGUES = {
    'nhl': ('hockey', 'nhl', 'NHL'),
    'nba': ('basketball', 'nba', 'NBA'),
    'mlb': ('baseball', 'mlb', 'MLB'),
    'nfl': ('football', 'nfl', 'NFL'),
    'ncaaf': ('football', 'college-football', 'NCAAF'),
    'ncaam': ('basketball', 'mens-college-basketball', 'NCAAM'),
}

# ESPN broadcast network name -> canonical Roku app name
# These map to the app_ids dict in roku.py
BROADCAST_TO_APP = {
    # ESPN family
    'espn': 'ESPN+',
    'espn+': 'ESPN+',
    'espn2': 'ESPN+',
    'espnu': 'ESPN+',
    'espnews': 'ESPN+',
    'espn deportes': 'ESPN+',
    'abc': 'ESPN+',            # ABC games available on ESPN app
    'sec network': 'ESPN+',
    'sec network+': 'ESPN+',
    'acc network': 'ESPN+',
    'acc network extra': 'ESPN+',
    'longhorn network': 'ESPN+',

    # NBC/Peacock family
    'nbc': 'Peacock',
    'peacock': 'Peacock',
    'nbcsn': 'Peacock',
    'usa network': 'Peacock',
    'cnbc': 'Peacock',

    # Fox family -> YouTube TV (no standalone Fox app on Roku)
    'fox': 'YouTubeTV',
    'fs1': 'YouTubeTV',
    'fs2': 'YouTubeTV',
    'fox sports 1': 'YouTubeTV',
    'fox sports 2': 'YouTubeTV',
    'fox deportes': 'YouTubeTV',
    'big ten network': 'YouTubeTV',
    'btn': 'YouTubeTV',

    # Turner/TNT/TBS -> YouTube TV
    'tnt': 'YouTubeTV',
    'tbs': 'YouTubeTV',
    'trutv': 'YouTubeTV',

    # CBS -> YouTube TV (Paramount+ not on user's Rokus)
    'cbs': 'YouTubeTV',
    'cbs sports network': 'YouTubeTV',
    'cbssn': 'YouTubeTV',

    # MLB specific
    'mlb network': 'MLB',
    'mlbn': 'MLB',
    'mlb.tv': 'MLB',
    'mlb tv': 'MLB',

    # NBA specific
    'nba tv': 'YouTubeTV',

    # NFL specific
    'nfl network': 'YouTubeTV',
    'nfl+': 'YouTubeTV',

    # NHL specific
    'nhl network': 'ESPN+',

    # Amazon
    'amazon prime video': 'Prime Video',
    'prime video': 'Prime Video',

    # Netflix (rare for live sports but possible)
    'netflix': 'Netflix',

    # Apple TV+ (no app on user's Rokus, fallback to YouTube TV)
    'apple tv+': 'YouTubeTV',

    # HULU
    'hulu': 'Hulu',
}

# Default app when broadcast not mapped
DEFAULT_APP = 'YouTubeTV'


class SportsScoreboard:
    """Fetches and formats ESPN scoreboard data with broadcast-to-app mapping"""

    def __init__(self):
        self._cache = {}
        self._cache_ttl = 60  # 60 seconds for live game data

    def _is_cache_valid(self, key: str) -> bool:
        if key not in self._cache:
            return False
        entry = self._cache[key]
        return (time.time() - entry['timestamp']) < self._cache_ttl

    async def fetch_all_games(self, sport: Optional[str] = None,
                               team: Optional[str] = None,
                               status_filter: Optional[str] = None) -> Dict[str, Any]:
        """Fetch games from ESPN scoreboard API.

        Args:
            sport: Optional league filter ('nhl', 'nba', 'mlb', 'nfl', 'ncaaf', 'ncaam')
            team: Optional team name to search for
            status_filter: Optional status filter ('live', 'upcoming', 'final')

        Returns:
            Dict with games grouped by league and metadata
        """
        cache_key = f"games:{sport or 'all'}"

        if self._is_cache_valid(cache_key) and not team:
            games = self._cache[cache_key]['data']
        else:
            games = await self._fetch_from_espn(sport)
            self._cache[cache_key] = {'data': games, 'timestamp': time.time()}

        # Apply filters
        if team:
            team_lower = team.lower()
            games = [g for g in games if self._game_matches_team(g, team_lower)]

        if status_filter:
            status_map = {'live': 'in', 'upcoming': 'pre', 'final': 'post'}
            espn_state = status_map.get(status_filter, status_filter)
            games = [g for g in games if g.get('status') == espn_state]

        # Sort: live first, then upcoming, then final
        games.sort(key=lambda g: {'in': 0, 'pre': 1, 'post': 2}.get(g.get('status', ''), 3))

        return {
            'games': games,
            'total': len(games),
            'timestamp': datetime.utcnow().isoformat(),
            'leagues': list(set(g.get('league', '') for g in games))
        }

    async def find_team_game(self, team_name: str) -> Optional[Dict[str, Any]]:
        """Find the current/upcoming game for a specific team.

        Prioritizes: live games > upcoming games > recently completed games.

        Args:
            team_name: Team name to search for (e.g., 'Penguins', 'Pittsburgh Penguins')

        Returns:
            Game dict with broadcast/app info, or None
        """
        result = await self.fetch_all_games(team=team_name)
        games = result.get('games', [])

        if not games:
            return None

        # Already sorted: live first, upcoming second, final last
        return games[0]

    async def _fetch_from_espn(self, sport: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch scoreboard data from ESPN API"""
        leagues_to_fetch = {}
        if sport and sport in LEAGUES:
            leagues_to_fetch = {sport: LEAGUES[sport]}
        else:
            leagues_to_fetch = LEAGUES

        all_games = []

        try:
            async with aiohttp.ClientSession() as session:
                tasks = []
                league_keys = []
                for key, (sport_path, league_path, display_name) in leagues_to_fetch.items():
                    url = f'{ESPN_API_BASE}/{sport_path}/{league_path}/scoreboard'
                    tasks.append(self._fetch_league(session, url, display_name))
                    league_keys.append(key)

                results = await asyncio.gather(*tasks, return_exceptions=True)

                for key, result in zip(league_keys, results):
                    if isinstance(result, Exception):
                        logger.warning(f"ESPN API error for {key}: {result}")
                    elif result:
                        all_games.extend(result)

        except Exception as e:
            logger.error(f"ESPN scoreboard fetch error: {e}")

        return all_games

    async def _fetch_league(self, session: aiohttp.ClientSession,
                             url: str, league_name: str) -> List[Dict[str, Any]]:
        """Fetch and format games for a single league"""
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                if resp.status != 200:
                    logger.warning(f"ESPN API returned {resp.status} for {url}")
                    return []
                data = await resp.json()
                events = data.get('events', [])
                return [self._format_game(event, league_name) for event in events]
        except Exception as e:
            logger.debug(f"ESPN fetch error for {league_name}: {e}")
            return []

    def _format_game(self, event: Dict, league_name: str) -> Dict[str, Any]:
        """Format an ESPN event into our game format"""
        competitions = event.get('competitions', [{}])
        competition = competitions[0] if competitions else {}
        competitors = competition.get('competitors', [])

        # Extract teams
        home_team = None
        away_team = None
        for comp in competitors:
            team_data = comp.get('team', {})
            team_info = {
                'name': team_data.get('displayName', 'TBD'),
                'short_name': team_data.get('shortDisplayName', 'TBD'),
                'abbreviation': team_data.get('abbreviation', ''),
                'location': team_data.get('location', ''),
                'nickname': team_data.get('name', ''),
                'logo': team_data.get('logo', ''),
                'color': team_data.get('color', '333333'),
                'score': comp.get('score', ''),
                'record': '',
            }
            # Extract record
            records = comp.get('records', [])
            if records:
                team_info['record'] = records[0].get('summary', '')

            if comp.get('homeAway') == 'home':
                home_team = team_info
            else:
                away_team = team_info

        if not home_team:
            home_team = {'name': 'TBD', 'short_name': 'TBD', 'abbreviation': '',
                         'location': '', 'nickname': '', 'logo': '', 'color': '333333',
                         'score': '', 'record': ''}
        if not away_team:
            away_team = dict(home_team)

        # Game status
        status_obj = event.get('status', {})
        status_type = status_obj.get('type', {})
        state = status_type.get('state', 'pre')
        status_detail = status_type.get('shortDetail', status_type.get('detail', ''))

        # Extract broadcast info
        broadcasts = self._extract_broadcasts(competition)
        watchable_apps = self._map_broadcasts_to_apps(broadcasts)

        # Venue
        venue = competition.get('venue', {})
        venue_name = venue.get('fullName', '')

        # Build game title
        if state in ('in', 'post') and home_team['score'] and away_team['score']:
            title = f"{away_team['short_name']} {away_team['score']} @ {home_team['short_name']} {home_team['score']}"
        else:
            title = f"{away_team['short_name']} @ {home_team['short_name']}"

        return {
            'id': f"espn_{event.get('id', '')}",
            'title': title,
            'home_team': home_team,
            'away_team': away_team,
            'status': state,
            'status_detail': status_detail,
            'league': league_name,
            'start_time': event.get('date', ''),
            'venue': venue_name,
            'broadcast_networks': broadcasts,
            'broadcast_display': ', '.join(broadcasts) if broadcasts else 'Check local listings',
            'watchable_apps': watchable_apps,
            'espn_link': '',
        }

    def _extract_broadcasts(self, competition: Dict) -> List[str]:
        """Extract broadcast network names from competition data.

        Checks geoBroadcasts (most detailed), then broadcasts, then broadcast string.
        """
        networks = []
        seen = set()

        # 1. Try geoBroadcasts (most detailed, has TV vs Streaming distinction)
        for gb in competition.get('geoBroadcasts', []):
            media = gb.get('media', {})
            name = media.get('shortName', '')
            if name and name.lower() not in seen:
                networks.append(name)
                seen.add(name.lower())

        if networks:
            return networks

        # 2. Try broadcasts array
        for broadcast in competition.get('broadcasts', []):
            for name in broadcast.get('names', []):
                name_str = str(name)
                if name_str and name_str.lower() not in seen:
                    networks.append(name_str)
                    seen.add(name_str.lower())

        if networks:
            return networks

        # 3. Fall back to simple broadcast string
        broadcast_str = competition.get('broadcast', '')
        if broadcast_str:
            # May contain "/" for multiple networks (e.g., "NBC/Peacock")
            for part in broadcast_str.split('/'):
                part = part.strip()
                if part and part.lower() not in seen:
                    networks.append(part)
                    seen.add(part.lower())

        return networks

    def _map_broadcasts_to_apps(self, networks: List[str]) -> List[Dict[str, str]]:
        """Map broadcast network names to launchable Roku apps.

        Returns list of {app_name, app_display, network} dicts.
        """
        apps = []
        seen_apps = set()

        # Roku app IDs (duplicated from roku.py to avoid circular import)
        APP_IDS = {
            'YouTubeTV': '195316',
            'ESPN+': '34376',
            'ESPN': '34376',
            'Peacock': '113072',
            'Prime Video': '13',
            'HBO Max': '61322',
            'Netflix': '12',
            'Hulu': '2285',
            'MLB': '14',
            'Disney+': '291097',
        }

        for network in networks:
            app_name = BROADCAST_TO_APP.get(network.lower(), None)
            if app_name and app_name not in seen_apps:
                seen_apps.add(app_name)
                apps.append({
                    'app_name': app_name,
                    'app_id': APP_IDS.get(app_name, ''),
                    'network': network,
                    'broadcast_name': network,  # Channel name for YouTube TV tuning
                })

        # If no specific mapping found, default to YouTube TV
        if not apps:
            apps.append({
                'app_name': DEFAULT_APP,
                'app_id': APP_IDS.get(DEFAULT_APP, ''),
                'network': 'YouTube TV',
            })

        return apps

    def _game_matches_team(self, game: Dict, team_lower: str) -> bool:
        """Check if a game involves the given team"""
        for side in ('home_team', 'away_team'):
            team = game.get(side, {})
            if (team_lower in team.get('name', '').lower() or
                team_lower in team.get('short_name', '').lower() or
                team_lower in team.get('nickname', '').lower() or
                team_lower in team.get('location', '').lower() or
                team_lower == team.get('abbreviation', '').lower()):
                return True
        return False


# Global instance
_scoreboard = None


def get_scoreboard() -> SportsScoreboard:
    global _scoreboard
    if _scoreboard is None:
        _scoreboard = SportsScoreboard()
    return _scoreboard
