"""
Rate limiting configuration for API endpoints
Protects against API flooding, brute force, and DoS attacks
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging

logger = logging.getLogger(__name__)


def create_rate_limiter():
    """
    Create and configure rate limiter for Flask application

    Returns:
        Configured Limiter instance
    """
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://"
    )
    return limiter


# Rate limiting strategies for different endpoint types
RATE_LIMITS = {
    # Search endpoints - moderate limits
    'search_all': '30 per minute, 300 per hour',
    'search_service': '20 per minute, 200 per hour',

    # TV control endpoints - strict limits
    'tv_power': '10 per minute, 100 per hour',
    'tv_volume': '20 per minute, 200 per hour',
    'tv_launch': '10 per minute, 100 per hour',
    'tv_input': '10 per minute, 100 per hour',
    'tv_status': '30 per minute, 300 per hour',

    # Voice endpoints - moderate limits
    'voice_transcribe': '20 per minute, 200 per hour',
    'voice_command': '30 per minute, 300 per hour',
    'voice_execute': '15 per minute, 150 per hour',
    'voice_sonos_speak': '20 per minute, 200 per hour',

    # Health check - generous limit
    'health': '100 per minute',
}


def apply_rate_limits(limiter, app):
    """
    Apply rate limits to Flask app routes

    Args:
        limiter: Limiter instance
        app: Flask application instance
    """
    # Search routes
    @app.route('/api/search/all', methods=['GET'])
    @limiter.limit(RATE_LIMITS['search_all'])
    def rate_limited_search_all():
        pass

    # TV control routes
    @app.route('/api/tv/power', methods=['POST'])
    @limiter.limit(RATE_LIMITS['tv_power'])
    def rate_limited_tv_power():
        pass

    @app.route('/api/tv/volume', methods=['POST'])
    @limiter.limit(RATE_LIMITS['tv_volume'])
    def rate_limited_tv_volume():
        pass

    @app.route('/api/tv/launch', methods=['POST'])
    @limiter.limit(RATE_LIMITS['tv_launch'])
    def rate_limited_tv_launch():
        pass

    # Voice routes
    @app.route('/api/voice/execute', methods=['POST'])
    @limiter.limit(RATE_LIMITS['voice_execute'])
    def rate_limited_voice_execute():
        pass

    @app.route('/api/voice/transcribe', methods=['POST'])
    @limiter.limit(RATE_LIMITS['voice_transcribe'])
    def rate_limited_voice_transcribe():
        pass

    # Health endpoint
    @app.route('/health', methods=['GET'])
    @limiter.limit(RATE_LIMITS['health'])
    def rate_limited_health():
        pass

    logger.info("Rate limiting configured for API endpoints")


def get_rate_limit(endpoint_name):
    """
    Get rate limit string for a specific endpoint

    Args:
        endpoint_name: Name of the endpoint (e.g., 'search_all')

    Returns:
        Rate limit string (e.g., '30 per minute, 300 per hour')
    """
    return RATE_LIMITS.get(endpoint_name, "200 per day, 50 per hour")
