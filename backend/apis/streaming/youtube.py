"""YouTube mock streaming service"""

import asyncio
from typing import List, Dict, Any
from . import SearchProvider


class YouTubeProvider(SearchProvider):
    """Mock YouTube content provider"""

    CONTENT = {
        'shows': [
            {
                'id': 'mrbeast',
                'title': 'MrBeast',
                'description': 'Popular entertainment and challenge videos',
                'poster': 'https://via.placeholder.com/150x225?text=MrBeast',
                'imdb_rating': 8.5,
                'release_year': 2012,
                'type': 'show'
            },
            {
                'id': 'vsauce',
                'title': 'Vsauce',
                'description': 'Educational science and technology videos',
                'poster': 'https://via.placeholder.com/150x225?text=Vsauce',
                'imdb_rating': 8.8,
                'release_year': 2010,
                'type': 'show'
            },
            {
                'id': 'veritasium',
                'title': 'Veritasium',
                'description': 'Educational videos about physics and science',
                'poster': 'https://via.placeholder.com/150x225?text=Veritasium',
                'imdb_rating': 8.9,
                'release_year': 2011,
                'type': 'show'
            },
            {
                'id': 'kurzgesagt',
                'title': 'Kurzgesagt',
                'description': 'Animated educational videos',
                'poster': 'https://via.placeholder.com/150x225?text=Kurzgesagt',
                'imdb_rating': 8.7,
                'release_year': 2013,
                'type': 'show'
            },
        ],
        'movies': [
            {
                'id': 'youtube_originals',
                'title': 'YouTube Originals',
                'description': 'Original content from YouTube creators',
                'poster': 'https://via.placeholder.com/150x225?text=YTOriginals',
                'imdb_rating': 7.8,
                'release_year': 2016,
                'type': 'movie'
            },
        ],
        'sports': [
            {
                'id': 'youtube_sports',
                'title': 'YouTube Sports',
                'description': 'Sports highlights and clips',
                'poster': 'https://via.placeholder.com/150x225?text=YTSports',
                'imdb_rating': 7.5,
                'release_year': 2015,
                'type': 'sports'
            },
        ]
    }

    def __init__(self):
        super().__init__('YouTube')

    async def search(self, query: str, content_type: str = 'all') -> List[Dict[str, Any]]:
        """Search YouTube content"""
        query_lower = query.lower()
        results = []

        search_types = ['shows', 'movies', 'sports']
        if content_type != 'all':
            type_map = {'show': 'shows', 'movie': 'movies', 'sports': 'sports'}
            search_types = [type_map.get(content_type, content_type)]

        for content_type_key in search_types:
            for content in self.CONTENT.get(content_type_key, []):
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

        await asyncio.sleep(0.1)
        return results

    async def get_details(self, content_id: str) -> Dict[str, Any]:
        """Get detailed information about content"""
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
