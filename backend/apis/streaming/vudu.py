"""Vudu mock streaming service"""

import asyncio
from typing import List, Dict, Any
from . import SearchProvider


class VuduProvider(SearchProvider):
    """Mock Vudu digital video retailer"""

    CONTENT = {
        'movies': [
            {
                'id': 'vudu_new_releases',
                'title': 'New Movie Releases',
                'description': 'Latest movies for rent or purchase',
                'poster': 'https://via.placeholder.com/150x225?text=NewReleases',
                'imdb_rating': 7.9,
                'release_year': 2024,
                'type': 'movie'
            },
            {
                'id': 'action_adventure',
                'title': 'Action & Adventure',
                'description': 'Thrilling action and adventure movies',
                'poster': 'https://via.placeholder.com/150x225?text=Action',
                'imdb_rating': 7.7,
                'release_year': 2024,
                'type': 'movie'
            },
            {
                'id': 'family_movies',
                'title': 'Family Movies',
                'description': 'Family-friendly entertainment',
                'poster': 'https://via.placeholder.com/150x225?text=Family',
                'imdb_rating': 7.6,
                'release_year': 2024,
                'type': 'movie'
            },
            {
                'id': 'classic_cinema',
                'title': 'Classic Cinema',
                'description': 'Timeless classics and historical films',
                'poster': 'https://via.placeholder.com/150x225?text=Classics',
                'imdb_rating': 8.2,
                'release_year': 1980,
                'type': 'movie'
            },
            {
                'id': 'indie_films',
                'title': 'Independent Films',
                'description': 'Indie and art house cinema',
                'poster': 'https://via.placeholder.com/150x225?text=Indie',
                'imdb_rating': 7.8,
                'release_year': 2023,
                'type': 'movie'
            },
            {
                'id': 'documentaries',
                'title': 'Documentaries',
                'description': 'Documentary films and features',
                'poster': 'https://via.placeholder.com/150x225?text=Docs',
                'imdb_rating': 8.0,
                'release_year': 2023,
                'type': 'movie'
            },
            {
                'id': 'thriller_mystery',
                'title': 'Thrillers & Mysteries',
                'description': 'Suspenseful thrillers and mysteries',
                'poster': 'https://via.placeholder.com/150x225?text=Thriller',
                'imdb_rating': 7.9,
                'release_year': 2023,
                'type': 'movie'
            },
            {
                'id': '4k_ultra_hd',
                'title': '4K Ultra HD',
                'description': 'Movies in 4K Ultra HD quality',
                'poster': 'https://via.placeholder.com/150x225?text=4K',
                'imdb_rating': 8.1,
                'release_year': 2023,
                'type': 'movie'
            },
        ],
        'shows': [
            {
                'id': 'vudu_originals',
                'title': 'Vudu Originals',
                'description': 'Original shows from Vudu',
                'poster': 'https://via.placeholder.com/150x225?text=VuduOrig',
                'imdb_rating': 7.5,
                'release_year': 2020,
                'type': 'show'
            },
        ]
    }

    def __init__(self):
        super().__init__('Vudu')

    async def search(self, query: str, content_type: str = 'all') -> List[Dict[str, Any]]:
        """Search Vudu content"""
        query_lower = query.lower()
        results = []

        search_types = ['movies', 'shows']
        if content_type != 'all':
            type_map = {'movie': 'movies', 'show': 'shows'}
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
        for content_type_key in ['movies', 'shows']:
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
