"""
VoiceTV Service - Main Flask Application
Main entry point for the VoiceTV backend service
"""

from flask import Flask, jsonify, send_from_directory, request
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

# Get production build path
FRONTEND_BUILD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend', 'build')
IS_PRODUCTION = os.path.exists(FRONTEND_BUILD_DIR) and os.path.exists(os.path.join(FRONTEND_BUILD_DIR, 'index.html'))

# Initialize Flask app
if IS_PRODUCTION:
    app = Flask(__name__, static_folder=FRONTEND_BUILD_DIR, static_url_path='')
    logger.info(f"Flask running in PRODUCTION mode, serving from {FRONTEND_BUILD_DIR}")
else:
    app = Flask(__name__)
    logger.warning("Production build not found. Running in API-only mode. Build React with: npm run build")

app.config.from_object(Config)

# Enable CORS for frontend communication
# In production, same-origin requests don't need CORS, but we allow localhost for dev
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5002", "http://127.0.0.1:5002"],
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
from routes.devices import devices_bp
from routes.alexa import alexa_bp
from routes.sports import sports_bp

# Register blueprints
app.register_blueprint(search_bp)
app.register_blueprint(tv_control_bp)
app.register_blueprint(voice_bp)
app.register_blueprint(devices_bp)
app.register_blueprint(alexa_bp)
app.register_blueprint(sports_bp)


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


@app.route('/test-api', methods=['GET', 'OPTIONS'])
def test_api():
    """Test endpoint to verify frontend can reach backend - helps diagnose connectivity issues"""
    if request.method == 'OPTIONS':
        return '', 200
    return jsonify({
        'message': 'Frontend successfully connected to backend API!',
        'timestamp': str(__import__('datetime').datetime.now()),
        'production': IS_PRODUCTION,
        'gunicorn': True
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


# Production: Serve React index.html for all non-API routes (React Router)
if IS_PRODUCTION:
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_react_app(path):
        """Serve React app for all non-API routes"""
        # If it's an API route, don't serve the app
        if path.startswith('api/'):
            return jsonify({'error': 'Not found'}), 404

        # If path is empty or it's a request for index.html, serve index.html
        if not path or path == 'index.html':
            full_path = os.path.join(FRONTEND_BUILD_DIR, 'index.html')
            if os.path.isfile(full_path):
                return send_from_directory(FRONTEND_BUILD_DIR, 'index.html')

        # If it's a static file, serve it
        full_path = os.path.join(FRONTEND_BUILD_DIR, path)
        if os.path.isfile(full_path):
            return send_from_directory(FRONTEND_BUILD_DIR, path)

        # Otherwise serve index.html (for React Router)
        index_path = os.path.join(FRONTEND_BUILD_DIR, 'index.html')
        if os.path.isfile(index_path):
            return send_from_directory(FRONTEND_BUILD_DIR, 'index.html')

        return jsonify({'error': 'Not found'}), 404


if __name__ == '__main__':
    if IS_PRODUCTION:
        logger.info("Starting VoiceTV Service in PRODUCTION on 0.0.0.0:5002")
        logger.warning("⚠️  Using Flask development server. For better performance, use: gunicorn -w 4 -b 0.0.0.0:5002 app:app")
        app.run(debug=False, host='0.0.0.0', port=5002)
    else:
        logger.error("❌ Production build not found! Build React first:")
        logger.error("   cd frontend && npm run build")
        sys.exit(1)
