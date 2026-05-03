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


def _apply_app_prioritization(game):
    """Apply YouTube TV prioritization to game watchable_apps.

    Simple rule: YouTube TV ALWAYS takes priority if available.

    Priority:
    1. If YouTube TV is in watchable_apps, move it to front
    2. If broadcast is on standard network, inject YouTube TV
    3. Otherwise use first available app
    """
    if not game:
        return game

    broadcast = game.get('broadcast_display', '').lower()
    apps = game.get('watchable_apps', [])

    if not apps:
        return game

    # PRIORITY 1: YouTube TV already in the list - move to front
    ytv_app = next((app for app in apps if app.get('app_name', '').lower() in ['youtubetv', 'youtube tv']), None)
    if ytv_app:
        apps.remove(ytv_app)
        apps.insert(0, ytv_app)
        logger.info(f"Game on {broadcast} - YouTube TV available, moving to top")
    else:
        # PRIORITY 2: Standard network broadcast - inject YouTube TV
        standard_networks = ['fox', 'cbs', 'nbc', 'abc', 'nbcsn', 'fs1', 'espn']
        has_standard_network = any(net in broadcast for net in standard_networks)

        if has_standard_network:
            # Extract the network name from broadcast_display (e.g., "NBC, Peacock" -> "NBC")
            network_name = broadcast.split(',')[0].strip()
            # Only use if it's a known network, not a streaming service
            if network_name.lower() not in ['peacock', 'espn+', 'hbo max']:
                ytv_app = {
                    'app_name': 'YouTubeTV',
                    'source': 'standard_network_inject',
                    'broadcast_name': network_name.upper(),
                    'network': network_name.upper()
                }
                apps.insert(0, ytv_app)
                logger.info(f"Standard network broadcast {broadcast} - injecting YouTube TV with network={network_name.upper()}")
            else:
                ytv_app = {'app_name': 'YouTubeTV', 'source': 'standard_network_inject'}
                apps.insert(0, ytv_app)
                logger.info(f"Standard network broadcast {broadcast} - injecting YouTube TV (streaming service)")

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
