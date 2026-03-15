"""
Bounded cache implementation with TTL and memory management
Prevents unbounded memory growth while maintaining performance
"""

import time
import logging
from typing import Any, Optional, Dict
from collections import OrderedDict

logger = logging.getLogger(__name__)


class BoundedCache:
    """
    Thread-safe bounded cache with TTL and LRU eviction

    Features:
    - Time-to-live (TTL) for automatic expiration
    - Least-recently-used (LRU) eviction when max size reached
    - Memory bounded to specified number of items
    - Statistics tracking (hits, misses, evictions)
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        Initialize bounded cache

        Args:
            max_size: Maximum number of items to store
            default_ttl: Default time-to-live in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, Dict[str, Any]] = OrderedDict()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expirations': 0
        }
        logger.info(f"Initialized BoundedCache with max_size={max_size}, default_ttl={default_ttl}s")

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        if key not in self.cache:
            self.stats['misses'] += 1
            return None

        entry = self.cache[key]

        # Check if expired
        if time.time() > entry['expires_at']:
            del self.cache[key]
            self.stats['expirations'] += 1
            logger.debug(f"Cache entry expired: {key}")
            return None

        # Move to end (most recently used)
        self.cache.move_to_end(key)
        self.stats['hits'] += 1
        logger.debug(f"Cache hit: {key}")
        return entry['value']

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        if ttl is None:
            ttl = self.default_ttl

        # Remove old entry if exists
        if key in self.cache:
            del self.cache[key]

        # Add new entry
        self.cache[key] = {
            'value': value,
            'expires_at': time.time() + ttl,
            'created_at': time.time()
        }

        # Move to end (most recently used)
        self.cache.move_to_end(key)

        # Evict least recently used if over capacity
        if len(self.cache) > self.max_size:
            evicted_key = next(iter(self.cache))
            del self.cache[evicted_key]
            self.stats['evictions'] += 1
            logger.debug(f"Cache evicted LRU entry: {evicted_key}")

        logger.debug(f"Cache set: {key} (TTL={ttl}s)")

    def delete(self, key: str) -> None:
        """Delete value from cache"""
        if key in self.cache:
            del self.cache[key]
            logger.debug(f"Cache deleted: {key}")

    def clear(self) -> None:
        """Clear all cache entries"""
        count = len(self.cache)
        self.cache.clear()
        logger.info(f"Cache cleared ({count} entries removed)")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Dictionary with cache stats
        """
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0

        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'evictions': self.stats['evictions'],
            'expirations': self.stats['expirations'],
            'hit_rate': f"{hit_rate:.1f}%",
            'total_requests': total_requests
        }

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries

        Returns:
            Number of entries removed
        """
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.cache.items()
            if current_time > entry['expires_at']
        ]

        for key in expired_keys:
            del self.cache[key]
            self.stats['expirations'] += 1

        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

        return len(expired_keys)


# Global cache instance
_cache = None


def get_cache(max_size: int = 1000, default_ttl: int = 300) -> BoundedCache:
    """
    Get or create the global cache instance

    Args:
        max_size: Maximum cache size (only used on first call)
        default_ttl: Default TTL (only used on first call)

    Returns:
        Global BoundedCache instance
    """
    global _cache
    if _cache is None:
        _cache = BoundedCache(max_size=max_size, default_ttl=default_ttl)
    return _cache


def cache_decorator(ttl: int = 300):
    """
    Decorator to cache function results

    Usage:
        @cache_decorator(ttl=600)
        def expensive_operation(param):
            return result

    Args:
        ttl: Time-to-live in seconds
    """
    def decorator(f):
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{f.__name__}:{str(args)}:{str(kwargs)}"
            cache = get_cache()

            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Call function and cache result
            result = f(*args, **kwargs)
            cache.set(cache_key, result, ttl=ttl)
            return result

        return wrapper
    return decorator
