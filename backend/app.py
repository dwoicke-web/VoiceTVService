"""
VoiceTV Service - Main Flask Application
Main entry point for the VoiceTV backend service
"""

from flask import Flask, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import sys
import logging

# Add backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from logging_config import setup_logging, get_logger
from auth import get_api_key_manager

# Setup structured logging
setup_logging()
logger = get_logger(__name__)

# Initialize API key management
api_key_manager = get_api_key_manager()
logger.info("API key manager initialized")

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Enable CORS for frontend communication (restricted to localhost in production)
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

logger.info("Flask application initialized with CORS and rate limiting")

# Import routes
from routes.search import search_bp
from routes.tv_control import tv_control_bp
from routes.voice import voice_bp

# Register blueprints
app.register_blueprint(search_bp)
app.register_blueprint(tv_control_bp)
app.register_blueprint(voice_bp)


@app.route('/health', methods=['GET'])
@limiter.limit("100 per minute")
def health():
    """Health check endpoint"""
    logger.debug("Health check requested")
    return jsonify({
        'status': 'healthy',
        'service': 'VoiceTV Service',
        'version': '0.2.0'
    }), 200


@app.route('/api/tvs', methods=['GET'])
def get_tvs():
    """Get available TVs in basement setup"""
    tvs = [
        {
            'id': 'big_screen',
            'name': 'Big Screen',
            'size': '75"',
            'type': 'Samsung Smart TV',
            'position': 'center',
            'status': 'online'
        },
        {
            'id': 'upper_right',
            'name': 'Upper Right',
            'size': '32"',
            'type': 'Amazon Fire TV',
            'position': 'upper_right',
            'status': 'online'
        },
        {
            'id': 'lower_right',
            'name': 'Lower Right',
            'size': '32"',
            'type': 'Amazon Fire TV',
            'position': 'lower_right',
            'status': 'online'
        },
        {
            'id': 'upper_left',
            'name': 'Upper Left',
            'size': '32"',
            'type': 'Amazon Fire TV',
            'position': 'upper_left',
            'status': 'online'
        },
        {
            'id': 'lower_left',
            'name': 'Lower Left',
            'size': '32"',
            'type': 'Amazon Fire TV',
            'position': 'lower_left',
            'status': 'online'
        }
    ]
    return jsonify({'tvs': tvs}), 200


@app.errorhandler(400)
def bad_request(error):
    """Handle bad request errors"""
    logger.warning(f"Bad request: {error}")
    return jsonify({
        'status': 'error',
        'error': 'Bad request',
        'message': str(error)
    }), 400


@app.errorhandler(401)
def unauthorized(error):
    """Handle unauthorized errors"""
    logger.warning("Unauthorized access attempt")
    return jsonify({
        'status': 'error',
        'error': 'Unauthorized',
        'message': 'Authentication required'
    }), 401


@app.errorhandler(403)
def forbidden(error):
    """Handle forbidden errors"""
    logger.warning("Access forbidden")
    return jsonify({
        'status': 'error',
        'error': 'Forbidden',
        'message': 'You do not have permission to access this resource'
    }), 403


@app.errorhandler(404)
def not_found(error):
    """Handle not found errors"""
    logger.info(f"Resource not found: {error}")
    return jsonify({
        'status': 'error',
        'error': 'Not found',
        'message': 'The requested resource was not found'
    }), 404


@app.errorhandler(429)
def rate_limit_exceeded(error):
    """Handle rate limit exceeded"""
    logger.warning(f"Rate limit exceeded from {get_remote_address()}")
    return jsonify({
        'status': 'error',
        'error': 'Too many requests',
        'message': 'Rate limit exceeded. Please try again later.'
    }), 429


@app.errorhandler(500)
def internal_server_error(error):
    """Handle internal server errors"""
    logger.error(f"Internal server error: {error}", exc_info=True)
    return jsonify({
        'status': 'error',
        'error': 'Internal server error',
        'message': 'An unexpected error occurred. Please try again later.'
    }), 500


if __name__ == '__main__':
    logger.info("Starting VoiceTV Service on 0.0.0.0:5002")
    app.run(debug=True, host='0.0.0.0', port=5002)
