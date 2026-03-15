"""Fandango mock streaming service"""

import asyncio
from typing import List, Dict, Any
from . import SearchProvider


class FandangoProvider(SearchProvider):
    """Mock Fandango movie and entertainment streaming provider"""

    CONTENT = {
        'movies': [
            {
                'id': 'latest_releases',
                'title': 'Latest Movie Releases',
                'description': 'New movies available for streaming and purchase',
                'poster': 'https://via.placeholder.com/150x225?text=NewReleases',
                'imdb_rating': 7.8,
                'release_year': 2023,
                'type': 'movie'
            },
            {
                'id': 'action_films',
                'title': 'Action Films',
                'description': 'Thrilling action-packed movies',
                'poster': 'https://via.placeholder.com/150x225?text=Action',
                'imdb_rating': 7.6,
                'release_year': 2023,
                'type': 'movie'
            },
            {
                'id': 'comedy_movies',
                'title': 'Comedy Movies',
                'description': 'Hilarious comedies to watch',
                'poster': 'https://via.placeholder.com/150x225?text=Comedy',
                'imdb_rating': 7.5,
                'release_year': 2023,
                'type': 'movie'
            },
            {
                'id': 'horror_films',
                'title': 'Horror Films',
                'description': 'Scary horror movies',
                'poster': 'https://via.placeholder.com/150x225?text=Horror',
                'imdb_rating': 7.4,
                'release_year': 2023,
                'type': 'movie'
            },
            {
                'id': 'drama_films',
                'title': 'Drama Films',
                'description': 'Compelling dramatic stories',
                'poster': 'https://via.placeholder.com/150x225?text=Drama',
                'imdb_rating': 7.9,
                'release_year': 2023,
                'type': 'movie'
            },
            {
                'id': 'sci_fi_movies',
                'title': 'Sci-Fi Movies',
                'description': 'Science fiction adventures',
                'poster': 'https://via.placeholder.com/150x225?text=SciFi',
                'imdb_rating': 7.7,
                'release_year': 2023,
                'type': 'movie'
            },
            {
                'id': 'animated_films',
                'title': 'Animated Films',
                'description': 'Family-friendly animated movies',
                'poster': 'https://via.placeholder.com/150x225?text=Animated',
                'imdb_rating': 7.8,
                'release_year': 2023,
                'type': 'movie'
            },
            {
                'id': 'romantic_movies',
                'title': 'Romance Movies',
                'description': 'Romantic comedy and drama films',
                'poster': 'https://via.placeholder.com/150x225?text=Romance',
                'imdb_rating': 7.3,
                'release_year': 2023,
                'type': 'movie'
            },
        ],
        'shows': [
            {
                'id': 'fandango_now',
                'title': 'Fandango Now Series',
                'description': 'Original series from Fandango',
                'poster': 'https://via.placeholder.com/150x225?text=FandangoNow',
                'imdb_rating': 7.6,
                'release_year': 2019,
                'type': 'show'
            },
        ]
    }

    def __init__(self):
        super().__init__('Fandango')

    async def search(self, query: str, content_type: str = 'all') -> List[Dict[str, Any]]:
        """Search Fandango content"""
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
