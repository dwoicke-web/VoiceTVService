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

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Sports league games error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@sports_bp.route('/team/<team_name>', methods=['GET'])
def get_team_game(team_name):
    """Find the current/upcoming game for a specific team.

    Returns the most relevant game (live > upcoming > final) and
    which streaming app to launch it on.

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
