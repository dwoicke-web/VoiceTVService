"""ESPN+ mock streaming service"""

import asyncio
from typing import List, Dict, Any
from . import SearchProvider


class ESPNPlusProvider(SearchProvider):
    """Mock ESPN+ sports content provider"""

    CONTENT = {
        'shows': [
            {
                'id': '30_for_30',
                'title': '30 for 30',
                'description': 'Acclaimed documentary series exploring significant sports events and figures',
                'poster': 'https://via.placeholder.com/150x225?text=30for30',
                'imdb_rating': 8.4,
                'release_year': 2009,
                'type': 'show'
            },
            {
                'id': 'around_the_horn',
                'title': 'Around the Horn',
                'description': 'A sports talk show where journalists debate the latest sports news',
                'poster': 'https://via.placeholder.com/150x225?text=AroundHorn',
                'imdb_rating': 7.6,
                'release_year': 2004,
                'type': 'show'
            },
            {
                'id': 'pardon_the_interruption',
                'title': 'Pardon the Interruption',
                'description': 'Hosts debate the hottest issues in sports with humor and insight',
                'poster': 'https://via.placeholder.com/150x225?text=PardonInt',
                'imdb_rating': 7.8,
                'release_year': 2001,
                'type': 'show'
            },
        ],
        'sports': [
            {
                'id': 'nfl_live',
                'title': 'NFL Live',
                'description': 'Live NFL games every week',
                'poster': 'https://via.placeholder.com/150x225?text=NFLLive',
                'imdb_rating': 8.5,
                'release_year': 2015,
                'type': 'sports'
            },
            {
                'id': 'college_football',
                'title': 'College Football',
                'description': 'Live college football games',
                'poster': 'https://via.placeholder.com/150x225?text=CollegeFB',
                'imdb_rating': 8.3,
                'release_year': 2010,
                'type': 'sports'
            },
            {
                'id': 'mlb_baseball',
                'title': 'MLB Baseball',
                'description': 'Live Major League Baseball games',
                'poster': 'https://via.placeholder.com/150x225?text=MLBBaseball',
                'imdb_rating': 8.1,
                'release_year': 2016,
                'type': 'sports'
            },
            {
                'id': 'nba_basketball',
                'title': 'NBA Basketball',
                'description': 'Live professional basketball games',
                'poster': 'https://via.placeholder.com/150x225?text=NBABasketball',
                'imdb_rating': 8.2,
                'release_year': 2018,
                'type': 'sports'
            },
            {
                'id': 'nhl_hockey',
                'title': 'NHL Hockey',
                'description': 'Live professional ice hockey games',
                'poster': 'https://via.placeholder.com/150x225?text=NHLHockey',
                'imdb_rating': 8.0,
                'release_year': 2020,
                'type': 'sports'
            },
            {
                'id': 'soccer_mls',
                'title': 'MLS Soccer',
                'description': 'Live Major League Soccer games',
                'poster': 'https://via.placeholder.com/150x225?text=MLSSoccer',
                'imdb_rating': 7.9,
                'release_year': 2017,
                'type': 'sports'
            },
            {
                'id': 'nfl_steelers',
                'title': 'Pittsburgh Steelers Live',
                'description': 'Live Pittsburgh Steelers NFL games',
                'poster': 'https://via.placeholder.com/150x225?text=Steelers',
                'imdb_rating': 8.4,
                'release_year': 2020,
                'type': 'sports'
            },
        ]
    }

    def __init__(self):
        super().__init__('ESPN+')

    async def search(self, query: str, content_type: str = 'all') -> List[Dict[str, Any]]:
        """Search ESPN+ content"""
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
