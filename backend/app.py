"""
VoiceTV Service - Main Flask Application
Main entry point for the VoiceTV backend service
"""

from flask import Flask, jsonify
from flask_cors import CORS
import os
import sys

# Add backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Enable CORS for frontend communication
CORS(app)

# Import routes
from routes.search import search_bp
from routes.tv_control import tv_control_bp

# Register blueprints
app.register_blueprint(search_bp)
app.register_blueprint(tv_control_bp)


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'VoiceTV Service',
        'version': '0.1.0'
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


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)
