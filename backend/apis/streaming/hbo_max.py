"""HBO Max mock streaming service"""

import asyncio
from typing import List, Dict, Any
from . import SearchProvider


class HBOMaxProvider(SearchProvider):
    """Mock HBO Max premium content provider"""

    CONTENT = {
        'shows': [
            {
                'id': 'game_of_thrones',
                'title': 'Game of Thrones',
                'description': 'A political thriller set in a fantasy world with intricate plots and complex characters',
                'poster': 'https://via.placeholder.com/150x225?text=GameOfThrones',
                'imdb_rating': 9.2,
                'release_year': 2011,
                'type': 'show'
            },
            {
                'id': 'true_detective',
                'title': 'True Detective',
                'description': 'A crime anthology series with changing stories and investigators each season',
                'poster': 'https://via.placeholder.com/150x225?text=TrueDetective',
                'imdb_rating': 8.4,
                'release_year': 2014,
                'type': 'show'
            },
            {
                'id': 'westworld',
                'title': 'Westworld',
                'description': 'An android-filled western theme park goes awry with consequences',
                'poster': 'https://via.placeholder.com/150x225?text=Westworld',
                'imdb_rating': 8.5,
                'release_year': 2016,
                'type': 'show'
            },
            {
                'id': 'succession',
                'title': 'Succession',
                'description': 'A ruthless dynasty battles for control of a global media empire',
                'poster': 'https://via.placeholder.com/150x225?text=Succession',
                'imdb_rating': 9.0,
                'release_year': 2018,
                'type': 'show'
            },
            {
                'id': 'the_white_lotus',
                'title': 'The White Lotus',
                'description': 'A mystery anthology series set at a luxury resort',
                'poster': 'https://via.placeholder.com/150x225?text=WhiteLotus',
                'imdb_rating': 8.3,
                'release_year': 2021,
                'type': 'show'
            },
            {
                'id': 'the_sopranos',
                'title': 'The Sopranos',
                'description': 'A crime drama about a New Jersey mob boss seeking therapy',
                'poster': 'https://via.placeholder.com/150x225?text=Sopranos',
                'imdb_rating': 9.2,
                'release_year': 1999,
                'type': 'show'
            },
        ],
        'movies': [
            {
                'id': 'the_dark_knight',
                'title': 'The Dark Knight',
                'description': 'Batman faces a criminal mastermind in Gotham City',
                'poster': 'https://via.placeholder.com/150x225?text=DarkKnight',
                'imdb_rating': 9.0,
                'release_year': 2008,
                'type': 'movie'
            },
            {
                'id': 'tenet',
                'title': 'Tenet',
                'description': 'A secret agent must prevent an international assassination',
                'poster': 'https://via.placeholder.com/150x225?text=Tenet',
                'imdb_rating': 7.3,
                'release_year': 2020,
                'type': 'movie'
            },
            {
                'id': 'dune',
                'title': 'Dune',
                'description': 'An epic science fiction adaptation of the classic novel',
                'poster': 'https://via.placeholder.com/150x225?text=Dune',
                'imdb_rating': 8.0,
                'release_year': 2021,
                'type': 'movie'
            },
            {
                'id': 'aquaman',
                'title': 'Aquaman',
                'description': 'A superhero discovers his underwater kingdom heritage',
                'poster': 'https://via.placeholder.com/150x225?text=Aquaman',
                'imdb_rating': 6.8,
                'release_year': 2018,
                'type': 'movie'
            },
        ],
    }

    def __init__(self):
        super().__init__('HBO Max')

    async def search(self, query: str, content_type: str = 'all') -> List[Dict[str, Any]]:
        """Search HBO Max content"""
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
