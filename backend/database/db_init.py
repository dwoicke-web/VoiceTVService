"""
Database initialization and setup for VoiceTV Service
"""

import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from .models import Base, TVConfiguration


def init_db(database_path='voicetv.db'):
    """
    Initialize the database and create all tables

    Args:
        database_path: Path to SQLite database file

    Returns:
        tuple: (engine, Session factory)
    """
    # Create absolute path
    if not database_path.startswith('/'):
        database_path = os.path.abspath(database_path)

    # Create connection string
    db_url = f'sqlite:///{database_path}'

    # Create engine with connection pooling
    engine = create_engine(
        db_url,
        connect_args={'check_same_thread': False},
        pool_pre_ping=True  # Verify connections before use
    )

    # Create all tables
    Base.metadata.create_all(engine)

    # Create session factory
    Session = scoped_session(sessionmaker(bind=engine))

    # Initialize default TV configuration if not already present
    _init_tv_configuration(Session)

    return engine, Session


def _init_tv_configuration(Session):
    """Initialize default TV configuration on first run"""
    session = Session()
    try:
        # Check if TVs already exist
        existing_tvs = session.query(TVConfiguration).count()

        if existing_tvs == 0:
            # Create default TV configuration
            tvs = [
                TVConfiguration(
                    tv_id='big_screen',
                    name='Big Screen',
                    size='75"',
                    tv_type='Samsung Smart TV',
                    position='center',
                    status='online'
                ),
                TVConfiguration(
                    tv_id='upper_right',
                    name='Upper Right',
                    size='32"',
                    tv_type='Amazon Fire TV',
                    position='upper_right',
                    status='online'
                ),
                TVConfiguration(
                    tv_id='lower_right',
                    name='Lower Right',
                    size='32"',
                    tv_type='Amazon Fire TV',
                    position='lower_right',
                    status='online'
                ),
                TVConfiguration(
                    tv_id='upper_left',
                    name='Upper Left',
                    size='32"',
                    tv_type='Amazon Fire TV',
                    position='upper_left',
                    status='online'
                ),
                TVConfiguration(
                    tv_id='lower_left',
                    name='Lower Left',
                    size='32"',
                    tv_type='Amazon Fire TV',
                    position='lower_left',
                    status='online'
                ),
            ]

            for tv in tvs:
                session.add(tv)

            session.commit()
            print("✓ Initialized default TV configuration")

    except Exception as e:
        session.rollback()
        print(f"Error initializing TV configuration: {e}")
    finally:
        session.close()


def get_db_session(Session):
    """
    Context manager for database sessions

    Usage:
        with get_db_session(Session) as session:
            results = session.query(Model).all()
    """
    class DBSession:
        def __init__(self, session_factory):
            self.session_factory = session_factory
            self.session = None

        def __enter__(self):
            self.session = self.session_factory()
            return self.session

        def __exit__(self, exc_type, exc_val, exc_tb):
            if self.session:
                self.session.close()

    return DBSession(Session)


def cleanup_expired_cache(Session, hours=24):
    """
    Clean up expired cache entries

    Args:
        Session: SQLAlchemy session factory
        hours: Remove cache older than this many hours (default: 24)
    """
    from .models import APICache, ContentCache

    session = Session()
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        # Clean up expired API cache
        expired_api = session.query(APICache).filter(
            APICache.cached_at < cutoff_time
        ).delete()

        # Clean up old content cache
        expired_content = session.query(ContentCache).filter(
            ContentCache.cached_at < cutoff_time
        ).delete()

        session.commit()
        print(f"✓ Cleaned up {expired_api + expired_content} cache entries")

    except Exception as e:
        session.rollback()
        print(f"Error cleaning cache: {e}")
    finally:
        session.close()
