"""
Database models for VoiceTV Service
Defines SQLAlchemy models for content cache, search history, and TV configuration
"""

from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class ContentCache(Base):
    """Cache for content search results"""
    __tablename__ = 'content_cache'

    id = Column(String(100), primary_key=True)  # Format: service_id_title
    title = Column(String(200), nullable=False, index=True)
    content_type = Column(String(20), nullable=False)  # show, movie, sports
    poster = Column(String(500))
    description = Column(Text)
    services = Column(JSON)  # List of available streaming services
    available_tvs = Column(JSON)  # List of TV IDs that can play this
    imdb_rating = Column(Float)
    release_year = Column(Integer)
    source_service = Column(String(50), nullable=False)  # Where this content came from
    cached_at = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<ContentCache({self.title}, {self.source_service})>"


class SearchHistory(Base):
    """Track search queries for suggestions and analytics"""
    __tablename__ = 'search_history'

    id = Column(Integer, primary_key=True)
    query = Column(String(200), nullable=False, index=True)
    content_type = Column(String(20))  # show, movie, sports, or all
    result_count = Column(Integer)
    search_time_ms = Column(Integer)  # How long the search took
    searched_at = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<SearchHistory(query='{self.query}', results={self.result_count})>"


class TVConfiguration(Base):
    """TV device configuration"""
    __tablename__ = 'tv_configuration'

    tv_id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    size = Column(String(10))  # e.g., "75\"", "32\""
    tv_type = Column(String(50))  # Samsung Smart TV, Amazon Fire TV, etc.
    position = Column(String(20))  # center, upper_left, upper_right, lower_left, lower_right
    status = Column(String(20), default='online')  # online, offline, error
    ip_address = Column(String(15))
    device_id = Column(String(100))  # Device ID for control API
    control_type = Column(String(50))  # smartthings, fire_tv, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<TVConfiguration({self.name}, {self.status})>"


class PlaybackHistory(Base):
    """Track what content was played on which TV"""
    __tablename__ = 'playback_history'

    id = Column(Integer, primary_key=True)
    tv_id = Column(String(50), nullable=False, index=True)
    content_title = Column(String(200), nullable=False)
    content_service = Column(String(50))
    played_at = Column(DateTime, default=datetime.utcnow, index=True)
    duration_seconds = Column(Integer)

    def __repr__(self):
        return f"<PlaybackHistory({self.content_title} on {self.tv_id})>"


class APICache(Base):
    """Cache for API responses to reduce load and improve response time"""
    __tablename__ = 'api_cache'

    id = Column(String(200), primary_key=True)  # Hash of query + params
    endpoint = Column(String(100), nullable=False, index=True)
    response_data = Column(JSON, nullable=False)
    cached_at = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, index=True)  # When cache expires

    def is_expired(self):
        """Check if cache has expired"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def __repr__(self):
        return f"<APICache(endpoint={self.endpoint}, expires={self.expires_at})>"
