"""
Configuration management for VoiceTV Service
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base configuration"""

    # Flask settings
    DEBUG = os.getenv('FLASK_DEBUG', False)
    TESTING = os.getenv('FLASK_TESTING', False)

    # Database
    DATABASE_PATH = os.getenv('DATABASE_PATH', './voicetv.db')

    # API Keys and Credentials
    YOUTUBE_TV_API_KEY = os.getenv('YOUTUBE_TV_API_KEY')
    PEACOCK_API_KEY = os.getenv('PEACOCK_API_KEY')
    PEACOCK_API_SECRET = os.getenv('PEACOCK_API_SECRET')
    ESPN_PLUS_API_KEY = os.getenv('ESPN_PLUS_API_KEY')
    AMAZON_PRIME_API_KEY = os.getenv('AMAZON_PRIME_API_KEY')
    HBO_MAX_API_KEY = os.getenv('HBO_MAX_API_KEY')

    # TV Control APIs
    SAMSUNG_SMARTTHINGS_TOKEN = os.getenv('SAMSUNG_SMARTTHINGS_TOKEN')
    SAMSUNG_SMARTTHINGS_DEVICE_ID = os.getenv('SAMSUNG_SMARTTHINGS_DEVICE_ID')

    # Speech Processing
    GOOGLE_CLOUD_API_KEY = os.getenv('GOOGLE_CLOUD_API_KEY')
    GOOGLE_CLOUD_PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT_ID')

    # Sonos
    SONOS_HOUSEHOLD_ID = os.getenv('SONOS_HOUSEHOLD_ID')
    SONOS_API_KEY = os.getenv('SONOS_API_KEY')

    # CORS settings
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DATABASE_PATH = ':memory:'
