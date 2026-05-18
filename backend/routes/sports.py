"""
Sports routes - ESPN live scoreboard with broadcast-to-app mapping.
Provides game schedules, scores, and which streaming app to launch.
"""

import asyncio
import logging
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)
sports_bp = Blueprint('sports', __name__, url_prefix='/api/sports')



def _get_or_create_event_loop():
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError
        return loop
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


def _find_ytv_channel(broadcast_display: str):
    """Return the first channel in broadcast_display that has a YTV deep-link mapping.

    National networks (NBC, ABC, CBS, FOX) are resolved to KC local affiliates
    before the lookup — matching fire_tv.tune_channel's affiliate map — so the
    caller gets back the national name (e.g. 'NBC') and tune_channel handles the
    KSHB/KMBC/KCTV5/FOX4 translation.
    """
    kc_affiliates = {'NBC': 'KSHB', 'ABC': 'KMBC', 'CBS': 'KCTV 5', 'FOX': 'FOX 4'}
    try:
        from apis.tv_control.ytv_channels import get_mapper
        mapper = get_mapper()
        for part in broadcast_display.split(','):
            name = part.strip().upper()
            lookup_name = kc_affiliates.get(name, name)
            if lookup_name and mapper.get_video_id(lookup_name):
                return name  # return national name; fire_tv.tune_channel maps to affiliate
    except Exception as e:
        logger.warning(f"YTV channel map lookup failed: {e}")
    return None


def _apply_app_prioritization(game):
    """Apply YouTube TV prioritization to game watchable_apps.

    Priority:
    1. If YouTube TV is in watchable_apps, move it to front; add broadcast_name if missing
    2. If any broadcast channel is in the YTV map, inject YouTube TV with that channel
    3. Fallback: inject YouTube TV without broadcast_name (generic launch)
    """
    if not game:
        return game

    broadcast_display = game.get('broadcast_display', '')
    apps = game.get('watchable_apps', [])

    if not apps:
        return game

    ytv_channel = _find_ytv_channel(broadcast_display)

    # PRIORITY 1: YouTube TV already in the list - move to front
    ytv_app = next((app for app in apps if app.get('app_name', '').lower() in ['youtubetv', 'youtube tv']), None)
    if ytv_app:
        apps.remove(ytv_app)
        # Add broadcast_name if missing and we found a mapped channel
        if ytv_channel and not ytv_app.get('broadcast_name'):
            ytv_app['broadcast_name'] = ytv_channel
            ytv_app['network'] = ytv_channel
        apps.insert(0, ytv_app)
        logger.info(f"Game on {broadcast_display} - YouTube TV available, moving to top, channel={ytv_app.get('broadcast_name')}")
    else:
        # PRIORITY 2: Inject YouTube TV - use mapped channel for direct tuning if available
        if ytv_channel:
            ytv_app = {
                'app_name': 'YouTubeTV',
                'source': 'ytv_map_inject',
                'broadcast_name': ytv_channel,
                'network': ytv_channel,
            }
            apps.insert(0, ytv_app)
            logger.info(f"Broadcast {broadcast_display} - injecting YouTube TV, channel={ytv_channel}")
        else:
            # Fallback: check hardcoded standard networks for backward compatibility
            standard_networks = ['fox', 'cbs', 'nbc', 'abc', 'nbcsn', 'fs1', 'espn', 'tnt', 'tbs']
            broadcast_lower = broadcast_display.lower()
            if any(net in broadcast_lower for net in standard_networks):
                ytv_app = {'app_name': 'YouTubeTV', 'source': 'standard_network_inject'}
                apps.insert(0, ytv_app)
                logger.info(f"Broadcast {broadcast_display} - injecting YouTube TV (no channel map, generic launch)")

    game['watchable_apps'] = apps
    return game


@sports_bp.route('/games', methods=['GET'])
def get_games():
    """Get live/upcoming/completed games from ESPN.

    Query params:
        sport: Filter by league (nhl, nba, mlb, nfl, ncaaf, ncaam)
        team: Search for a specific team name
        status: Filter by status (live, upcoming, final)

    Returns all games across all major leagues by default.
    """
    try:
        from apis.sports import get_scoreboard

        sport = request.args.get('sport')
        team = request.args.get('team')
        status_filter = request.args.get('status')

        scoreboard = get_scoreboard()
        loop = _get_or_create_event_loop()
        result = loop.run_until_complete(
            scoreboard.fetch_all_games(sport=sport, team=team, status_filter=status_filter)
        )

        # Apply YouTube TV prioritization to all games
        if result and 'games' in result:
            result['games'] = [_apply_app_prioritization(game) for game in result['games']]

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Sports games error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@sports_bp.route('/games/<league>', methods=['GET'])
def get_league_games(league):
    """Get games for a specific league.

    Path params:
        league: nhl, nba, mlb, nfl, ncaaf, ncaam
    """
    try:
        from apis.sports import get_scoreboard

        scoreboard = get_scoreboard()
        loop = _get_or_create_event_loop()
        result = loop.run_until_complete(
            scoreboard.fetch_all_games(sport=league)
        )

        # Apply YouTube TV prioritization to all games
        if result and 'games' in result:
            result['games'] = [_apply_app_prioritization(game) for game in result['games']]

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Sports league games error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@sports_bp.route('/team/<team_name>', methods=['GET'])
def get_team_game(team_name):
    """Find the current/upcoming game for a specific team.

    Returns the most relevant game (live > upcoming > final) and
    which streaming app to launch it on. Prioritizes YouTube TV.

    Path params:
        team_name: Team name (e.g., 'penguins', 'pittsburgh penguins', 'PIT')
    """
    try:
        from apis.sports import get_scoreboard

        scoreboard = get_scoreboard()
        loop = _get_or_create_event_loop()
        game = loop.run_until_complete(
            scoreboard.find_team_game(team_name)
        )

        # Apply YouTube TV prioritization to the game data
        if game:
            game = _apply_app_prioritization(game)

        if not game:
            return jsonify({
                'found': False,
                'message': f'No games found for {team_name}',
                'team': team_name
            }), 404

        return jsonify({
            'found': True,
            'game': game,
            'team': team_name
        }), 200

    except Exception as e:
        logger.error(f"Sports team game error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
