"""JustWatch mock streaming service discovery platform"""

import asyncio
from typing import List, Dict, Any
from . import SearchProvider


class JustWatchProvider(SearchProvider):
    """Mock JustWatch content discovery platform"""

    CONTENT = {
        'movies': [
            {
                'id': 'popular_movies',
                'title': 'Popular Movies This Week',
                'description': 'Trending movies across all streaming platforms',
                'poster': 'https://via.placeholder.com/150x225?text=Popular',
                'imdb_rating': 7.8,
                'release_year': 2024,
                'type': 'movie'
            },
            {
                'id': 'trending_movies',
                'title': 'Trending Now',
                'description': 'Movies trending on JustWatch',
                'poster': 'https://via.placeholder.com/150x225?text=Trending',
                'imdb_rating': 7.9,
                'release_year': 2024,
                'type': 'movie'
            },
            {
                'id': 'superhero_movies',
                'title': 'Superhero Movies',
                'description': 'Superhero and comic book adaptations',
                'poster': 'https://via.placeholder.com/150x225?text=Superhero',
                'imdb_rating': 7.6,
                'release_year': 2024,
                'type': 'movie'
            },
            {
                'id': 'drama_movies',
                'title': 'Drama Films',
                'description': 'Award-winning drama movies',
                'poster': 'https://via.placeholder.com/150x225?text=Drama',
                'imdb_rating': 8.1,
                'release_year': 2024,
                'type': 'movie'
            },
            {
                'id': 'animated_movies',
                'title': 'Animated Films',
                'description': 'Animated movies for all ages',
                'poster': 'https://via.placeholder.com/150x225?text=Animated',
                'imdb_rating': 7.9,
                'release_year': 2024,
                'type': 'movie'
            },
            {
                'id': 'horror_movies',
                'title': 'Horror & Suspense',
                'description': 'Horror and suspenseful films',
                'poster': 'https://via.placeholder.com/150x225?text=Horror',
                'imdb_rating': 7.5,
                'release_year': 2023,
                'type': 'movie'
            },
            {
                'id': 'romantic_movies',
                'title': 'Romance & Love Stories',
                'description': 'Romantic comedies and dramas',
                'poster': 'https://via.placeholder.com/150x225?text=Romance',
                'imdb_rating': 7.4,
                'release_year': 2023,
                'type': 'movie'
            },
            {
                'id': 'sci_fi_movies',
                'title': 'Sci-Fi & Fantasy',
                'description': 'Science fiction and fantasy movies',
                'poster': 'https://via.placeholder.com/150x225?text=SciFi',
                'imdb_rating': 7.8,
                'release_year': 2024,
                'type': 'movie'
            },
        ],
        'shows': [
            {
                'id': 'top_shows',
                'title': 'Top-Rated TV Shows',
                'description': 'Highest-rated shows across platforms',
                'poster': 'https://via.placeholder.com/150x225?text=TopShows',
                'imdb_rating': 8.6,
                'release_year': 2024,
                'type': 'show'
            },
            {
                'id': 'binge_worthy',
                'title': 'Binge-Worthy Series',
                'description': 'Best series to watch in one sitting',
                'poster': 'https://via.placeholder.com/150x225?text=Binge',
                'imdb_rating': 8.4,
                'release_year': 2023,
                'type': 'show'
            },
            {
                'id': 'limited_series',
                'title': 'Limited Series',
                'description': 'Miniseries and limited run shows',
                'poster': 'https://via.placeholder.com/150x225?text=Limited',
                'imdb_rating': 8.5,
                'release_year': 2024,
                'type': 'show'
            },
            {
                'id': 'comedy_shows',
                'title': 'Comedy Series',
                'description': 'Funny sitcoms and comedy specials',
                'poster': 'https://via.placeholder.com/150x225?text=Comedy',
                'imdb_rating': 7.9,
                'release_year': 2024,
                'type': 'show'
            },
        ]
    }

    def __init__(self):
        super().__init__('JustWatch')

    async def search(self, query: str, content_type: str = 'all') -> List[Dict[str, Any]]:
        """Search JustWatch content"""
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
