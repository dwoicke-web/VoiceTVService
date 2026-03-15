"""
API authentication and authorization
Provides token-based authentication for API endpoints
"""

from flask import request, jsonify
from functools import wraps
import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class APIKeyManager:
    """Manage API keys for authentication"""

    def __init__(self):
        """Initialize API key manager from environment"""
        # In production, these would be stored in a database with hash verification
        # For now, using environment variables for development
        self.valid_keys = set()
        self._load_keys()

    def _load_keys(self):
        """Load API keys from environment"""
        # Load from environment variable (comma-separated)
        keys_env = os.getenv('VOICETV_API_KEYS', '')
        if keys_env:
            self.valid_keys = set(key.strip() for key in keys_env.split(',') if key.strip())
            logger.info(f"Loaded {len(self.valid_keys)} API keys from environment")
        else:
            # Default key for development
            self.valid_keys.add('dev-key-12345')
            logger.warning("Using default development API key. Set VOICETV_API_KEYS environment variable for production")

    def is_valid_key(self, key: str) -> bool:
        """Check if API key is valid"""
        return key in self.valid_keys

    def add_key(self, key: str) -> None:
        """Add a new API key"""
        self.valid_keys.add(key)
        logger.info(f"API key added")

    def remove_key(self, key: str) -> None:
        """Remove an API key"""
        self.valid_keys.discard(key)
        logger.info(f"API key removed")


# Global API key manager instance
_api_key_manager = None


def get_api_key_manager() -> APIKeyManager:
    """Get or create the global API key manager"""
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager()
    return _api_key_manager


def extract_api_key() -> Optional[str]:
    """
    Extract API key from request headers or query parameters

    Supports:
    - Authorization: Bearer <key> header
    - X-API-Key: <key> header
    - ?api_key=<key> query parameter

    Returns:
        API key string or None if not found
    """
    # Check Authorization header (Bearer token)
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]

    # Check X-API-Key header
    api_key_header = request.headers.get('X-API-Key')
    if api_key_header:
        return api_key_header

    # Check query parameter
    query_key = request.args.get('api_key')
    if query_key:
        return query_key

    return None


def require_api_key(f):
    """
    Decorator to require API key authentication on a route

    Usage:
        @app.route('/api/protected')
        @require_api_key
        def protected_endpoint():
            return jsonify({'status': 'authorized'})
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = extract_api_key()

        if not api_key:
            logger.warning(f"Request without API key from {request.remote_addr}")
            return jsonify({
                'status': 'error',
                'error': 'Unauthorized',
                'message': 'API key required. Provide via Authorization header, X-API-Key header, or api_key parameter'
            }), 401

        manager = get_api_key_manager()
        if not manager.is_valid_key(api_key):
            logger.warning(f"Invalid API key attempt from {request.remote_addr}")
            return jsonify({
                'status': 'error',
                'error': 'Unauthorized',
                'message': 'Invalid API key'
            }), 401

        # Key is valid, continue with the request
        logger.debug(f"Valid API key authentication from {request.remote_addr}")
        return f(*args, **kwargs)

    return decorated_function


def require_api_key_optional(f):
    """
    Decorator for optional API key authentication
    Allows requests with or without API key, but tracks usage

    Usage:
        @app.route('/api/public')
        @require_api_key_optional
        def public_endpoint():
            return jsonify({'status': 'ok'})
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = extract_api_key()

        if api_key:
            manager = get_api_key_manager()
            if not manager.is_valid_key(api_key):
                logger.warning(f"Invalid API key from {request.remote_addr}")
                return jsonify({
                    'status': 'error',
                    'error': 'Unauthorized',
                    'message': 'Invalid API key'
                }), 401
            logger.debug(f"Request with valid API key from {request.remote_addr}")
        else:
            logger.debug(f"Unauthenticated request from {request.remote_addr}")

        return f(*args, **kwargs)

    return decorated_function
