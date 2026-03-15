"""
Streaming service providers for VoiceTV Service
Each service implements the SearchProvider interface for unified searching
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
import asyncio


class SearchProvider(ABC):
    """Base class for streaming service providers"""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour default cache TTL

    @abstractmethod
    async def search(self, query: str, content_type: str = 'all') -> List[Dict[str, Any]]:
        """
        Search for content in this service

        Args:
            query: Search query string
            content_type: 'show', 'movie', 'sports', or 'all'

        Returns:
            List of content results with standard format
        """
        pass

    @abstractmethod
    async def get_details(self, content_id: str) -> Dict[str, Any]:
        """Get detailed information about a piece of content"""
        pass

    def _format_result(self,
                      content_id: str,
                      title: str,
                      content_type: str,
                      description: str = "",
                      poster: str = "",
                      imdb_rating: float = None,
                      release_year: int = None,
                      available_tvs: List[str] = None) -> Dict[str, Any]:
        """
        Format search result in standard format

        Args:
            content_id: Unique ID for this content
            title: Content title
            content_type: 'show', 'movie', or 'sports'
            description: Brief description
            poster: URL to poster image
            imdb_rating: IMDB rating if available
            release_year: Year released
            available_tvs: Which TVs can play this

        Returns:
            Formatted result dictionary
        """
        if available_tvs is None:
            available_tvs = ['big_screen', 'upper_right', 'lower_right', 'upper_left', 'lower_left']

        return {
            'id': f"{self.service_name}_{content_id}",
            'title': title,
            'type': content_type,
            'poster': poster,
            'description': description,
            'available_services': [self.service_name],
            'available_tvs': available_tvs,
            'imdb_rating': imdb_rating,
            'release_year': release_year,
            'source_service': self.service_name
        }

    async def search_multiple(self, queries: List[str], content_type: str = 'all') -> List[Dict[str, Any]]:
        """
        Search for multiple queries concurrently

        Args:
            queries: List of search queries
            content_type: Content type filter

        Returns:
            Combined list of results
        """
        tasks = [self.search(q, content_type) for q in queries]
        results = await asyncio.gather(*tasks)
        # Flatten and deduplicate results
        all_results = []
        seen_ids = set()
        for result_list in results:
            for result in result_list:
                if result['id'] not in seen_ids:
                    all_results.append(result)
                    seen_ids.add(result['id'])
        return all_results

    def __repr__(self):
        return f"<SearchProvider({self.service_name})>"
