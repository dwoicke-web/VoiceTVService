"""Amazon Prime Video mock streaming service"""

import asyncio
from typing import List, Dict, Any
from . import SearchProvider


class PrimeVideoProvider(SearchProvider):
    """Mock Amazon Prime Video content provider"""

    CONTENT = {
        'shows': [
            {
                'id': 'the_boys',
                'title': 'The Boys',
                'description': 'A group of vigilantes set out to take down corrupt superheroes who abuse their powers',
                'poster': 'https://via.placeholder.com/150x225?text=TheBoys',
                'imdb_rating': 8.7,
                'release_year': 2019,
                'type': 'show'
            },
            {
                'id': 'the_marvelous_mrs_maisel',
                'title': 'The Marvelous Mrs. Maisel',
                'description': 'A housewife in the 1950s discovers she has a talent for stand-up comedy',
                'poster': 'https://via.placeholder.com/150x225?text=MrsMaisel',
                'imdb_rating': 8.7,
                'release_year': 2017,
                'type': 'show'
            },
            {
                'id': 'the_neighbors',
                'title': 'The Neighbors',
                'description': 'A family discovers their new neighbors are actually aliens',
                'poster': 'https://via.placeholder.com/150x225?text=TheNeighbors',
                'imdb_rating': 7.4,
                'release_year': 2012,
                'type': 'show'
            },
        ],
        'movies': [
            {
                'id': 'the_grand_tour',
                'title': 'The Grand Tour',
                'description': 'Three car enthusiasts travel around the world in exotic vehicles',
                'poster': 'https://via.placeholder.com/150x225?text=GrandTour',
                'imdb_rating': 8.5,
                'release_year': 2016,
                'type': 'show'
            },
            {
                'id': 'borat',
                'title': 'Borat',
                'description': 'A Kazakhstani journalist travels to America with hilarious results',
                'poster': 'https://via.placeholder.com/150x225?text=Borat',
                'imdb_rating': 7.4,
                'release_year': 2006,
                'type': 'movie'
            },
            {
                'id': 'pirates_of_caribbean',
                'title': 'Pirates of the Caribbean',
                'description': 'A swashbuckling adventure with pirates, treasure, and curses',
                'poster': 'https://via.placeholder.com/150x225?text=PiratesCaribbean',
                'imdb_rating': 8.1,
                'release_year': 2003,
                'type': 'movie'
            },
            {
                'id': 'the_terminal',
                'title': 'The Terminal',
                'description': 'A traveler gets stuck in an airport terminal',
                'poster': 'https://via.placeholder.com/150x225?text=Terminal',
                'imdb_rating': 7.7,
                'release_year': 2004,
                'type': 'movie'
            },
        ],
    }

    def __init__(self):
        super().__init__('Amazon Prime')

    async def search(self, query: str, content_type: str = 'all') -> List[Dict[str, Any]]:
        """Search Amazon Prime Video content"""
        query_lower = query.lower()
        results = []

        search_types = ['shows', 'movies']
        if content_type != 'all':
            type_map = {'show': 'shows', 'movie': 'movies'}
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
        for content_type_key in ['shows', 'movies']:
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
