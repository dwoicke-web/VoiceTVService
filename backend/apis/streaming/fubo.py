"""Fubo mock streaming service"""

import asyncio
from typing import List, Dict, Any
from . import SearchProvider


class FuboProvider(SearchProvider):
    """Mock Fubo sports and entertainment streaming provider"""

    CONTENT = {
        'shows': [
            {
                'id': 'fubo_live_sports',
                'title': 'Fubo Live Sports',
                'description': 'Live sports channels 24/7',
                'poster': 'https://via.placeholder.com/150x225?text=FuboSports',
                'imdb_rating': 8.2,
                'release_year': 2015,
                'type': 'show'
            },
            {
                'id': 'sports_highlights',
                'title': 'Sports Highlights',
                'description': 'Latest sports highlights and replays',
                'poster': 'https://via.placeholder.com/150x225?text=Highlights',
                'imdb_rating': 7.9,
                'release_year': 2016,
                'type': 'show'
            },
        ],
        'sports': [
            {
                'id': 'nfl_games',
                'title': 'NFL Games Live',
                'description': 'Live NFL games every week',
                'poster': 'https://via.placeholder.com/150x225?text=NFLLive',
                'imdb_rating': 8.6,
                'release_year': 2015,
                'type': 'sports'
            },
            {
                'id': 'soccer_leagues',
                'title': 'International Soccer',
                'description': 'Live soccer games from major leagues',
                'poster': 'https://via.placeholder.com/150x225?text=Soccer',
                'imdb_rating': 8.4,
                'release_year': 2016,
                'type': 'sports'
            },
            {
                'id': 'college_sports',
                'title': 'College Sports',
                'description': 'Live college football, basketball, and more',
                'poster': 'https://via.placeholder.com/150x225?text=College',
                'imdb_rating': 8.3,
                'release_year': 2017,
                'type': 'sports'
            },
            {
                'id': 'tennis_matches',
                'title': 'Tennis Matches',
                'description': 'Live tennis tournaments',
                'poster': 'https://via.placeholder.com/150x225?text=Tennis',
                'imdb_rating': 8.1,
                'release_year': 2018,
                'type': 'sports'
            },
            {
                'id': 'mma_boxing',
                'title': 'MMA & Boxing',
                'description': 'Live MMA and boxing events',
                'poster': 'https://via.placeholder.com/150x225?text=MMA',
                'imdb_rating': 8.3,
                'release_year': 2016,
                'type': 'sports'
            },
            {
                'id': 'rugby_cricket',
                'title': 'Rugby & Cricket',
                'description': 'Live rugby and cricket matches',
                'poster': 'https://via.placeholder.com/150x225?text=Rugby',
                'imdb_rating': 8.0,
                'release_year': 2017,
                'type': 'sports'
            },
        ]
    }

    def __init__(self):
        super().__init__('Fubo')

    async def search(self, query: str, content_type: str = 'all') -> List[Dict[str, Any]]:
        """Search Fubo content"""
        query_lower = query.lower()
        results = []

        search_types = ['shows', 'sports']
        if content_type != 'all':
            type_map = {'show': 'shows', 'sports': 'sports'}
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
        for content_type_key in ['shows', 'sports']:
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
