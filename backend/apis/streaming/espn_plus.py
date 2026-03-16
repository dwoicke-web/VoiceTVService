"""ESPN Live Sports provider - queries ESPN's public API for live/upcoming games"""

import asyncio
import aiohttp
import logging
from typing import List, Dict, Any
from datetime import datetime
from . import SearchProvider

logger = logging.getLogger(__name__)

# All major ESPN sport/league endpoints
ESPN_LEAGUES = [
    ('football', 'nfl'),
    ('basketball', 'nba'),
    ('baseball', 'mlb'),
    ('hockey', 'nhl'),
    ('soccer', 'usa.1'),           # MLS
    ('football', 'college-football'),
    ('basketball', 'mens-college-basketball'),
    ('basketball', 'womens-college-basketball'),
    ('soccer', 'eng.1'),           # EPL
    ('soccer', 'uefa.champions'),  # Champions League
]

ESPN_API_BASE = 'https://site.api.espn.com/apis/site/v2/sports'


class ESPNPlusProvider(SearchProvider):
    """Real ESPN live sports provider using ESPN's public scoreboard API"""

    def __init__(self):
        super().__init__('ESPN')

    async def _fetch_scoreboard(self, session: aiohttp.ClientSession,
                                 sport: str, league: str) -> List[Dict]:
        """Fetch scoreboard data for a specific sport/league"""
        url = f'{ESPN_API_BASE}/{sport}/{league}/scoreboard'
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    events = data.get('events', [])
                    # Tag each event with sport/league info for matching
                    league_name = data.get('leagues', [{}])[0].get('name', '') if data.get('leagues') else ''
                    league_abbrev = data.get('leagues', [{}])[0].get('abbreviation', '') if data.get('leagues') else ''
                    for event in events:
                        event['_sport'] = sport
                        event['_league'] = league
                        event['_league_name'] = league_name
                        event['_league_abbrev'] = league_abbrev
                    return events
        except Exception as e:
            logger.debug(f"ESPN API error for {sport}/{league}: {e}")
        return []

    def _match_query(self, event: Dict, query_lower: str) -> bool:
        """Check if an event matches the search query"""
        # Check event name
        name = event.get('name', '').lower()
        short_name = event.get('shortName', '').lower()

        if query_lower in name or query_lower in short_name:
            return True

        # Check sport and league names
        sport = event.get('_sport', '').lower()
        league = event.get('_league', '').lower()
        league_name = event.get('_league_name', '').lower()
        league_abbrev = event.get('_league_abbrev', '').lower()

        if (query_lower in sport or
            query_lower in league or
            query_lower in league_name or
            query_lower == league_abbrev):
            return True

        # Check team names
        for competition in event.get('competitions', []):
            for competitor in competition.get('competitors', []):
                team = competitor.get('team', {})
                team_name = team.get('displayName', '').lower()
                team_short = team.get('shortDisplayName', '').lower()
                team_abbrev = team.get('abbreviation', '').lower()
                team_location = team.get('location', '').lower()
                team_nickname = team.get('name', '').lower()

                if (query_lower in team_name or
                    query_lower in team_short or
                    query_lower == team_abbrev or
                    query_lower in team_location or
                    query_lower in team_nickname):
                    return True

        return False

    def _format_event(self, event: Dict) -> Dict[str, Any]:
        """Format an ESPN event into our standard result format"""
        competitions = event.get('competitions', [{}])
        competition = competitions[0] if competitions else {}
        competitors = competition.get('competitors', [])

        # Build team info
        teams = []
        scores = []
        logos = []
        for comp in competitors:
            team = comp.get('team', {})
            teams.append(team.get('displayName', 'TBD'))
            scores.append(comp.get('score', ''))
            logo = team.get('logo', '')
            if logo:
                logos.append(logo)

        # Get game status
        status_obj = event.get('status', {})
        status_type = status_obj.get('type', {})
        status_name = status_type.get('name', '')
        status_detail = status_type.get('shortDetail', status_type.get('detail', ''))
        status_state = status_type.get('state', '')

        # Determine display status
        if status_state == 'in':
            game_status = f"LIVE - {status_detail}"
            status_emoji = "🔴"
        elif status_state == 'pre':
            game_status = f"Upcoming - {status_detail}"
            status_emoji = "🟡"
        elif status_state == 'post':
            game_status = f"Final - {status_detail}"
            status_emoji = "✅"
        else:
            game_status = status_detail or status_name
            status_emoji = "⚪"

        # Build title
        if len(teams) >= 2:
            if scores[0] and scores[1] and status_state in ('in', 'post'):
                title = f"{teams[0]} {scores[0]} vs {teams[1]} {scores[1]}"
            else:
                title = f"{teams[0]} vs {teams[1]}"
        else:
            title = event.get('name', 'Unknown Event')

        # Get broadcast info
        broadcasts = []
        for broadcast in competition.get('broadcasts', []):
            for name_obj in broadcast.get('names', []):
                broadcasts.append(name_obj if isinstance(name_obj, str) else str(name_obj))
        broadcast_str = ', '.join(broadcasts) if broadcasts else 'ESPN+'

        # Get league info
        league_name = event.get('_league_abbrev', '') or event.get('_league', '')

        # Build description
        description = f"{status_emoji} {game_status}"
        if broadcast_str:
            description += f" | 📺 {broadcast_str}"
        if league_name:
            description += f" | {league_name}"

        # Use first team logo as poster, or ESPN logo
        poster = logos[0] if logos else 'https://a.espncdn.com/combiner/i?img=/i/teamlogos/default-team-logo-500.png&w=150&h=150'

        return self._format_result(
            content_id=event.get('id', 'unknown'),
            title=title,
            content_type='sports',
            description=description,
            poster=poster,
            imdb_rating=None,
            release_year=None,
            available_tvs=['upper_right', 'lower_right', 'upper_left', 'lower_left']
        )

    async def search(self, query: str, content_type: str = 'all') -> List[Dict[str, Any]]:
        """Search ESPN for live/upcoming games matching the query"""
        if content_type not in ('all', 'sports'):
            return []

        query_lower = query.lower().strip()
        if not query_lower:
            return []

        results = []

        try:
            async with aiohttp.ClientSession() as session:
                # Fetch all leagues in parallel
                tasks = [
                    self._fetch_scoreboard(session, sport, league)
                    for sport, league in ESPN_LEAGUES
                ]
                all_events_by_league = await asyncio.gather(*tasks)

                # Search through all events
                seen_ids = set()
                for events in all_events_by_league:
                    for event in events:
                        event_id = event.get('id', '')
                        if event_id in seen_ids:
                            continue

                        if self._match_query(event, query_lower):
                            seen_ids.add(event_id)
                            formatted = self._format_event(event)
                            results.append(formatted)

        except Exception as e:
            logger.error(f"ESPN search error: {e}")

        # Sort: live games first, then upcoming, then completed
        def sort_key(r):
            desc = r.get('description', '')
            if '🔴' in desc:
                return 0  # Live first
            elif '🟡' in desc:
                return 1  # Upcoming second
            else:
                return 2  # Final last
        results.sort(key=sort_key)

        return results

    async def get_details(self, content_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific event"""
        return {}
