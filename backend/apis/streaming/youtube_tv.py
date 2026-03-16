"""YouTube TV streaming service with real API integration"""

import asyncio
import os
import logging
from typing import List, Dict, Any
import aiohttp
from . import SearchProvider

logger = logging.getLogger(__name__)


class YouTubeTVProvider(SearchProvider):
    """YouTube TV content provider with real API support"""

    def __init__(self):
        super().__init__('YouTubeTV')
        self.api_key = os.getenv('YOUTUBE_TV_API_KEY')
        self.base_url = 'https://www.googleapis.com/youtube/v3'

    # Mock content database
    CONTENT = {
        'shows': [
            {
                'id': 'breaking_bad',
                'title': 'Breaking Bad',
                'description': 'A high school chemistry teacher diagnosed with inoperable lung cancer turns to cooking methamphetamine with a former student.',
                'poster': 'https://via.placeholder.com/150x225?text=BreakingBad',
                'imdb_rating': 9.5,
                'release_year': 2008,
                'type': 'show'
            },
            {
                'id': 'strangers_things',
                'title': 'Stranger Things',
                'description': 'When a young boy disappears, his friends, family and local police uncover a mystery involving secret government experiments and a strange creature.',
                'poster': 'https://via.placeholder.com/150x225?text=StrangerThings',
                'imdb_rating': 8.7,
                'release_year': 2016,
                'type': 'show'
            },
            {
                'id': 'the_office',
                'title': 'The Office',
                'description': 'A mockumentary on a group of typical office workers, where the workday consists of ego clashes, inappropriate behavior, and tedium.',
                'poster': 'https://via.placeholder.com/150x225?text=TheOffice',
                'imdb_rating': 9.0,
                'release_year': 2005,
                'type': 'show'
            },
            {
                'id': 'friends',
                'title': 'Friends',
                'description': 'Follows the personal and professional lives of six twenty to thirty year-old friends living in Manhattan.',
                'poster': 'https://via.placeholder.com/150x225?text=Friends',
                'imdb_rating': 8.9,
                'release_year': 1994,
                'type': 'show'
            },
            {
                'id': 'the_crown',
                'title': 'The Crown',
                'description': 'Follows the political rivalries and romance of Queen Elizabeth II\'s reign and the events that shaped the second half of the twentieth century.',
                'poster': 'https://via.placeholder.com/150x225?text=TheCrown',
                'imdb_rating': 8.6,
                'release_year': 2016,
                'type': 'show'
            },
        ],
        'movies': [
            {
                'id': 'inception',
                'title': 'Inception',
                'description': 'A skilled thief who steals corporate secrets through the use of dream-sharing technology is given the inverse task of planting an idea.',
                'poster': 'https://via.placeholder.com/150x225?text=Inception',
                'imdb_rating': 8.8,
                'release_year': 2010,
                'type': 'movie'
            },
            {
                'id': 'the_matrix',
                'title': 'The Matrix',
                'description': 'A computer hacker learns from mysterious rebels about the true nature of his reality and his role in the war against its controllers.',
                'poster': 'https://via.placeholder.com/150x225?text=TheMatrix',
                'imdb_rating': 8.7,
                'release_year': 1999,
                'type': 'movie'
            },
            {
                'id': 'interstellar',
                'title': 'Interstellar',
                'description': 'A team of explorers travel through a wormhole in space in an attempt to ensure humanity\'s survival.',
                'poster': 'https://via.placeholder.com/150x225?text=Interstellar',
                'imdb_rating': 8.6,
                'release_year': 2014,
                'type': 'movie'
            },
        ],
        'sports': [
            {
                'id': 'nfl_game_sunday',
                'title': 'NFL Sunday Night Football',
                'description': 'Live professional football games every Sunday night',
                'poster': 'https://via.placeholder.com/150x225?text=NFL',
                'imdb_rating': 8.4,
                'release_year': 2006,
                'type': 'sports'
            },
            {
                'id': 'nba_basketball',
                'title': 'NBA Basketball',
                'description': 'Professional basketball league games',
                'poster': 'https://via.placeholder.com/150x225?text=NBA',
                'imdb_rating': 8.2,
                'release_year': 1946,
                'type': 'sports'
            },
        ]
    }

    async def search(self, query: str, content_type: str = 'all') -> List[Dict[str, Any]]:
        """
        Search YouTube TV content using real API or mock data

        Args:
            query: Search query
            content_type: Filter by 'show', 'movie', 'sports', or 'all'

        Returns:
            List of matching content
        """
        if self.api_key and self.api_key != 'your_youtube_tv_api_key_here':
            try:
                logger.info(f"Using real YouTube API for query: {query}")
                return await self._search_real_api(query, content_type)
            except Exception as e:
                logger.warning(f"Real API search failed, falling back to mock data: {e}")
                return await self._search_mock(query, content_type)
        else:
            logger.info(f"Using mock data for YouTube TV search: {query}")
            return await self._search_mock(query, content_type)

    async def _search_mock(self, query: str, content_type: str = 'all') -> List[Dict[str, Any]]:
        """Search through mock content database"""
        query_lower = query.lower()
        results = []

        # Determine which content types to search
        search_types = ['shows', 'movies', 'sports']
        if content_type != 'all':
            # Map content_type to our internal keys
            type_map = {
                'show': 'shows',
                'movie': 'movies',
                'sports': 'sports'
            }
            search_types = [type_map.get(content_type, content_type)]

        # Search through content
        for content_type_key in search_types:
            for content in self.CONTENT.get(content_type_key, []):
                # Match on title or description
                if (query_lower in content['title'].lower() or
                    query_lower in content['description'].lower()):
                    results.append(self._format_result(
                        content_id=content['id'],
                        title=content['title'],
                        content_type=content['type'],
                        description=content['description'],
                        poster=content['poster'],
                        imdb_rating=content.get('imdb_rating'),
                        release_year=content.get('release_year')
                    ))

        # Simulate search delay
        await asyncio.sleep(0.1)
        return results

    async def _search_real_api(self, query: str, content_type: str = 'all') -> List[Dict[str, Any]]:
        """Search YouTube using the real YouTube Data API v3"""
        results = []

        try:
            async with aiohttp.ClientSession() as session:
                # Search for videos
                search_url = f"{self.base_url}/search"
                params = {
                    'q': query,
                    'part': 'snippet',
                    'type': 'video',
                    'maxResults': 10,
                    'key': self.api_key,
                    'relevanceLanguage': 'en'
                }

                async with session.get(search_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()

                        for item in data.get('items', []):
                            snippet = item.get('snippet', {})
                            video_id = item.get('id', {}).get('videoId')

                            if video_id:
                                results.append(self._format_result(
                                    content_id=video_id,
                                    title=snippet.get('title', 'Unknown'),
                                    content_type='show',
                                    description=snippet.get('description', ''),
                                    poster=snippet.get('thumbnails', {}).get('medium', {}).get('url', ''),
                                    imdb_rating=None,
                                    release_year=None
                                ))
                    else:
                        logger.error(f"YouTube API error: {response.status}")

        except Exception as e:
            logger.error(f"Error calling YouTube API: {e}")
            raise

        return results

    async def get_details(self, content_id: str) -> Dict[str, Any]:
        """Get detailed information about content"""
        # Search through all content to find matching ID
        for content_type_key in ['shows', 'movies', 'sports']:
            for content in self.CONTENT.get(content_type_key, []):
                if content['id'] == content_id:
                    return self._format_result(
                        content_id=content['id'],
                        title=content['title'],
                        content_type=content['type'],
                        description=content['description'],
                        poster=content['poster'],
                        imdb_rating=content.get('imdb_rating'),
                        release_year=content.get('release_year')
                    )
        return {}
