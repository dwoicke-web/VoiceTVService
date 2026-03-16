"""
Unified search engine for VoiceTV Service
Aggregates results from all streaming services with deduplication and ranking
"""

import asyncio
import hashlib
from typing import List, Dict, Any
from datetime import datetime, timedelta
from .streaming import SearchProvider
from .streaming.youtube_tv import YouTubeTVProvider
from .streaming.youtube import YouTubeProvider
from .streaming.peacock import PeacockProvider
from .streaming.espn_plus import ESPNPlusProvider
from .streaming.prime_video import PrimeVideoProvider
from .streaming.hbo_max import HBOMaxProvider
from .streaming.fandango import FandangoProvider
from .streaming.vudu import VuduProvider
from .streaming.justwatch import JustWatchProvider


class SearchAggregator:
    """Aggregates search results from multiple streaming services"""

    def __init__(self):
        """Initialize search aggregator with all streaming providers"""
        self.providers: List[SearchProvider] = [
            YouTubeTVProvider(),
            YouTubeProvider(),
            PeacockProvider(),
            ESPNPlusProvider(),
            PrimeVideoProvider(),
            HBOMaxProvider(),
            FandangoProvider(),
            VuduProvider(),
            JustWatchProvider(),
        ]
        self.cache: Dict[str, Dict[str, Any]] = {}  # In-memory cache
        self.cache_ttl = 300  # 5 minutes cache TTL

    def _get_cache_key(self, query: str, content_type: str) -> str:
        """Generate cache key from query and content type"""
        key_str = f"{query}:{content_type}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid"""
        if cache_key not in self.cache:
            return False

        cache_entry = self.cache[cache_key]
        if 'timestamp' not in cache_entry:
            return False

        age = datetime.utcnow() - cache_entry['timestamp']
        return age < timedelta(seconds=self.cache_ttl)

    async def search(self, query: str, content_type: str = 'all') -> Dict[str, Any]:
        """
        Search across all streaming services

        Args:
            query: Search query string
            content_type: Filter by 'show', 'movie', 'sports', or 'all'

        Returns:
            Dictionary with aggregated results and metadata
        """
        cache_key = self._get_cache_key(query, content_type)

        # Check cache first
        if self._is_cache_valid(cache_key):
            print(f"Cache hit for: {query}")
            return self.cache[cache_key]['data']

        print(f"Cache miss - searching: {query}")

        # Search all providers in parallel
        tasks = [
            provider.search(query, content_type)
            for provider in self.providers
        ]

        start_time = datetime.utcnow()
        results_by_service = await asyncio.gather(*tasks, return_exceptions=True)
        search_time = (datetime.utcnow() - start_time).total_seconds()

        # Combine results from all services
        all_results = []

        for provider, result in zip(self.providers, results_by_service):
            if isinstance(result, Exception):
                print(f"Error searching {provider.service_name}: {result}")
            else:
                all_results.extend(result)

        # Deduplicate and rank results
        ranked_results = self._deduplicate_and_rank(all_results)

        # Services the user cares about, in display order
        MY_SERVICES = [
            'YouTube TV', 'Netflix', 'ESPN', 'Prime Video', 'HBO Max',
            'MLB', 'Disney+', 'Hulu', 'Peacock', 'YouTube', 'Vudu',
        ]

        # Map JustWatch variant names to our canonical service names
        SERVICE_NORMALIZE = {
            'youtubetv': 'YouTube TV',
            'youtube tv': 'YouTube TV',
            'netflix': 'Netflix',
            'netflix standard with ads': 'Netflix',
            'netflix basic with ads': 'Netflix',
            'espn': 'ESPN',
            'espn+': 'ESPN',
            'espn plus': 'ESPN',
            'amazon prime video': 'Prime Video',
            'amazon prime video with ads': 'Prime Video',
            'amazon video': 'Prime Video',
            'prime video': 'Prime Video',
            'hbo max': 'HBO Max',
            'hbo max amazon channel': 'HBO Max',
            'max': 'HBO Max',
            'max amazon channel': 'HBO Max',
            'mlb': 'MLB',
            'mlb.tv': 'MLB',
            'mlb tv': 'MLB',
            'disney plus': 'Disney+',
            'disney+': 'Disney+',
            'hulu': 'Hulu',
            'peacock': 'Peacock',
            'peacock premium': 'Peacock',
            'peacock premium plus': 'Peacock',
            'youtube': 'YouTube',
            'vudu': 'Vudu',
            'fandango at home': 'Vudu',
            'fandango at home free': 'Vudu',
        }

        # Normalize available_services on each result to canonical names
        for result in ranked_results:
            raw_services = result.get('available_services', [])
            normalized = []
            seen = set()
            for svc in raw_services:
                canonical = SERVICE_NORMALIZE.get(svc.lower(), svc)
                if canonical not in seen:
                    normalized.append(canonical)
                    seen.add(canonical)
            result['available_services'] = normalized

        # Build service breakdown from only the services the user cares about
        service_breakdown = {svc: 0 for svc in MY_SERVICES}
        for result in ranked_results:
            for svc in result.get('available_services', []):
                if svc in service_breakdown:
                    service_breakdown[svc] += 1

        # Remove services with 0 results, keep display order
        service_breakdown = {k: v for k, v in service_breakdown.items() if v > 0}

        # Prepare response
        response = {
            'query': query,
            'content_type': content_type,
            'results': ranked_results,
            'total': len(ranked_results),
            'search_time_ms': int(search_time * 1000),
            'service_breakdown': service_breakdown,
            'timestamp': datetime.utcnow().isoformat()
        }

        # Cache the result
        self.cache[cache_key] = {
            'data': response,
            'timestamp': datetime.utcnow()
        }

        return response

    def _deduplicate_and_rank(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deduplicate results (same title from different services = same content)
        and rank by relevance

        Args:
            results: List of results from all services

        Returns:
            Deduplicated and ranked results
        """
        # Group by title (case-insensitive)
        title_map: Dict[str, List[Dict[str, Any]]] = {}

        for result in results:
            title_key = result['title'].lower()

            if title_key not in title_map:
                title_map[title_key] = []

            title_map[title_key].append(result)

        # Merge duplicate entries
        merged_results = []

        for title_key, result_group in title_map.items():
            if len(result_group) == 1:
                merged_results.append(result_group[0])
            else:
                # Merge multiple entries for same content
                merged = self._merge_duplicate_results(result_group)
                merged_results.append(merged)

        # Sort by relevance
        ranked = self._rank_results(merged_results)

        return ranked

    def _merge_duplicate_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge multiple results for the same content from different services

        Args:
            results: List of result objects for the same content

        Returns:
            Merged result with combined services
        """
        # Start with the first result as base
        merged = results[0].copy()

        # Collect all services
        all_services = set(merged.get('available_services', []))
        all_tvs = set(merged.get('available_tvs', []))

        for result in results[1:]:
            all_services.update(result.get('available_services', []))
            all_tvs.update(result.get('available_tvs', []))

            # Use highest rating
            if result.get('imdb_rating') and merged.get('imdb_rating'):
                merged['imdb_rating'] = max(
                    merged['imdb_rating'],
                    result['imdb_rating']
                )

        merged['available_services'] = list(all_services)
        merged['available_tvs'] = list(all_tvs)

        return merged

    def _rank_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Rank results by relevance and quality

        Args:
            results: Results to rank

        Returns:
            Ranked results
        """
        # Sort by:
        # 1. Number of services (more is better)
        # 2. IMDB rating (higher is better)
        # 3. Release year (newer is better, but not critically)

        def sort_key(result):
            num_services = len(result.get('available_services', []))
            imdb_rating = result.get('imdb_rating', 0) or 0
            year = result.get('release_year', 0) or 0

            return (
                -num_services,      # More services = higher priority
                -imdb_rating,       # Higher rating = higher priority
                -year,              # Newer = higher priority (tie-breaker)
            )

        return sorted(results, key=sort_key)

    def clear_cache(self):
        """Clear the search cache"""
        self.cache.clear()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        valid_entries = sum(
            1 for key in self.cache
            if self._is_cache_valid(key)
        )

        return {
            'total_entries': len(self.cache),
            'valid_entries': valid_entries,
            'expired_entries': len(self.cache) - valid_entries,
            'cache_ttl_seconds': self.cache_ttl
        }


# Global search aggregator instance
_search_aggregator = None


def get_search_aggregator() -> SearchAggregator:
    """Get or create the global search aggregator"""
    global _search_aggregator
    if _search_aggregator is None:
        _search_aggregator = SearchAggregator()
    return _search_aggregator
