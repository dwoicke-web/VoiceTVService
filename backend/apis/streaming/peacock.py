"""Peacock mock streaming service"""

import asyncio
from typing import List, Dict, Any
from . import SearchProvider


class PeacockProvider(SearchProvider):
    """Mock Peacock content provider (NBCUniversal)"""

    CONTENT = {
        'shows': [
            {
                'id': 'the_office_nbc',
                'title': 'The Office',
                'description': 'A comedic mockumentary about everyday office workers',
                'poster': 'https://via.placeholder.com/150x225?text=TheOfficeNBC',
                'imdb_rating': 9.0,
                'release_year': 2005,
                'type': 'show'
            },
            {
                'id': 'parks_and_rec',
                'title': 'Parks and Recreation',
                'description': 'The quirky staff of a municipal government office in a small Indiana town',
                'poster': 'https://via.placeholder.com/150x225?text=ParksRec',
                'imdb_rating': 8.6,
                'release_year': 2009,
                'type': 'show'
            },
            {
                'id': 'the_good_place',
                'title': 'The Good Place',
                'description': 'Eleanor Shellstrop, an ordinary woman, is accidentally sent to the "good place" instead of the "bad place" after her death.',
                'poster': 'https://via.placeholder.com/150x225?text=GoodPlace',
                'imdb_rating': 8.3,
                'release_year': 2016,
                'type': 'show'
            },
            {
                'id': 'law_and_order',
                'title': 'Law & Order',
                'description': 'A crime drama about the investigation and prosecution of criminals',
                'poster': 'https://via.placeholder.com/150x225?text=LawOrder',
                'imdb_rating': 7.8,
                'release_year': 1990,
                'type': 'show'
            },
        ],
        'movies': [
            {
                'id': 'meet_the_parents',
                'title': 'Meet the Parents',
                'description': 'A man must win over his girlfriend\'s intimidating father during a weekend getaway',
                'poster': 'https://via.placeholder.com/150x225?text=MeetParents',
                'imdb_rating': 7.3,
                'release_year': 2000,
                'type': 'movie'
            },
            {
                'id': 'notting_hill',
                'title': 'Notting Hill',
                'description': 'A London bookstore owner falls in love with a famous American actress',
                'poster': 'https://via.placeholder.com/150x225?text=NottingHill',
                'imdb_rating': 7.1,
                'release_year': 1999,
                'type': 'movie'
            },
            {
                'id': 'four_rooms',
                'title': 'Four Rooms',
                'description': 'A bellhop deals with wild guests checking into a luxurious hotel on New Year\'s Eve',
                'poster': 'https://via.placeholder.com/150x225?text=FourRooms',
                'imdb_rating': 6.4,
                'release_year': 1995,
                'type': 'movie'
            },
        ],
        'sports': [
            {
                'id': 'nbc_sports',
                'title': 'NBC Sports Live',
                'description': 'Live sports coverage from NBC',
                'poster': 'https://via.placeholder.com/150x225?text=NBCSports',
                'imdb_rating': 7.9,
                'release_year': 2010,
                'type': 'sports'
            },
        ]
    }

    def __init__(self):
        super().__init__('Peacock')

    async def search(self, query: str, content_type: str = 'all') -> List[Dict[str, Any]]:
        """Search Peacock content"""
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
