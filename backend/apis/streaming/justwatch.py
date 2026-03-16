"""JustWatch real streaming service discovery - queries JustWatch GraphQL API"""

import asyncio
import aiohttp
import logging
from typing import List, Dict, Any
from . import SearchProvider

logger = logging.getLogger(__name__)

JUSTWATCH_GRAPHQL_URL = 'https://apis.justwatch.com/graphql'
JUSTWATCH_IMAGE_BASE = 'https://images.justwatch.com'

SEARCH_QUERY = """
query GetSearchTitles($searchTitlesFilter: TitleFilter!, $country: Country!, $language: Language!) {
  popularTitles(country: $country, filter: $searchTitlesFilter, first: 15) {
    edges {
      node {
        id
        objectId
        objectType
        content(country: $country, language: $language) {
          title
          fullPath
          originalReleaseYear
          shortDescription
          genres { shortName }
          posterUrl
          externalIds { imdbId }
        }
        offers(country: $country, platform: WEB) {
          monetizationType
          presentationType
          package {
            packageId
            clearName
            icon
          }
        }
      }
    }
  }
}
"""

# Map JustWatch genre codes to readable names
GENRE_MAP = {
    'act': 'Action',
    'ani': 'Animation',
    'cmy': 'Comedy',
    'crm': 'Crime',
    'doc': 'Documentary',
    'drm': 'Drama',
    'fnt': 'Fantasy',
    'hrr': 'Horror',
    'hst': 'History',
    'msc': 'Music',
    'mys': 'Mystery',
    'rma': 'Romance',
    'scf': 'Sci-Fi',
    'spt': 'Sport',
    'trl': 'Thriller',
    'war': 'War',
    'wsn': 'Western',
    'fml': 'Family',
    'eur': 'European',
    'rly': 'Reality',
}

# Map monetization types to readable labels
MONETIZATION_MAP = {
    'FLATRATE': 'Stream',
    'RENT': 'Rent',
    'BUY': 'Buy',
    'FREE': 'Free',
    'ADS': 'Free with Ads',
}


class JustWatchProvider(SearchProvider):
    """Real JustWatch provider using GraphQL API for streaming availability"""

    def __init__(self):
        super().__init__('JustWatch')

    def _build_poster_url(self, poster_path: str) -> str:
        """Build full poster URL from JustWatch path template"""
        if not poster_path:
            return 'https://via.placeholder.com/150x225?text=No+Poster'
        # Replace template variables with actual values
        url = poster_path.replace('{profile}', 's592').replace('{format}', 'webp')
        return f'{JUSTWATCH_IMAGE_BASE}{url}'

    def _get_streaming_services(self, offers: List[Dict]) -> List[str]:
        """Extract unique streaming services from offers, preferring FLATRATE/FREE"""
        if not offers:
            return []

        # Group by service, prioritizing flatrate (subscription) offers
        services = {}
        for offer in offers:
            service_name = offer.get('package', {}).get('clearName', '')
            if not service_name:
                continue
            mon_type = offer.get('monetizationType', '')
            # Track best monetization type per service
            if service_name not in services:
                services[service_name] = mon_type
            elif mon_type == 'FLATRATE' or mon_type == 'FREE':
                services[service_name] = mon_type

        return list(services.keys())

    def _build_description(self, node: Dict) -> str:
        """Build a description string from JustWatch node data"""
        content = node.get('content', {})
        parts = []

        # Short description
        short_desc = content.get('shortDescription', '')
        if short_desc:
            # Truncate long descriptions
            if len(short_desc) > 200:
                short_desc = short_desc[:197] + '...'
            parts.append(short_desc)

        # Genres
        genres = content.get('genres', [])
        if genres:
            genre_names = [GENRE_MAP.get(g.get('shortName', ''), g.get('shortName', ''))
                          for g in genres]
            parts.append(f"Genres: {', '.join(genre_names)}")

        # Streaming availability summary
        offers = node.get('offers', [])
        if offers:
            # Get unique services with their monetization types
            service_info = {}
            for offer in offers:
                service_name = offer.get('package', {}).get('clearName', '')
                mon_type = offer.get('monetizationType', '')
                if service_name and service_name not in service_info:
                    service_info[service_name] = MONETIZATION_MAP.get(mon_type, mon_type)

            if service_info:
                avail_parts = [f"{name} ({mtype})" for name, mtype in list(service_info.items())[:5]]
                parts.append(f"📺 Available on: {', '.join(avail_parts)}")

        return ' | '.join(parts) if parts else 'No description available'

    def _format_node(self, node: Dict) -> Dict[str, Any]:
        """Format a JustWatch GraphQL node into our standard result format"""
        content = node.get('content', {})
        object_type = node.get('objectType', 'MOVIE')

        # Map JustWatch types to our types
        if object_type == 'SHOW':
            content_type = 'show'
        else:
            content_type = 'movie'

        title = content.get('title', 'Unknown')
        year = content.get('originalReleaseYear')
        poster_path = content.get('posterUrl', '')
        poster_url = self._build_poster_url(poster_path)
        description = self._build_description(node)
        streaming_services = self._get_streaming_services(node.get('offers', []))

        result = self._format_result(
            content_id=str(node.get('objectId', node.get('id', 'unknown'))),
            title=title,
            content_type=content_type,
            description=description,
            poster=poster_url,
            imdb_rating=None,
            release_year=year,
            available_tvs=['upper_right', 'lower_right', 'upper_left', 'lower_left']
        )

        # Override available_services with actual streaming services from JustWatch
        if streaming_services:
            result['available_services'] = streaming_services
        else:
            result['available_services'] = ['No streaming info']

        return result

    async def search(self, query: str, content_type: str = 'all') -> List[Dict[str, Any]]:
        """Search JustWatch for movies and TV shows"""
        if content_type == 'sports':
            return []

        query_stripped = query.strip()
        if not query_stripped:
            return []

        results = []

        try:
            variables = {
                'searchTitlesFilter': {'searchQuery': query_stripped},
                'country': 'US',
                'language': 'en'
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    JUSTWATCH_GRAPHQL_URL,
                    json={'query': SEARCH_QUERY, 'variables': variables},
                    timeout=aiohttp.ClientTimeout(total=8)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        edges = (data.get('data', {})
                                .get('popularTitles', {})
                                .get('edges', []))

                        for edge in edges:
                            node = edge.get('node', {})
                            object_type = node.get('objectType', '')

                            # Filter by content type if specified
                            if content_type == 'movie' and object_type != 'MOVIE':
                                continue
                            if content_type == 'show' and object_type != 'SHOW':
                                continue

                            formatted = self._format_node(node)
                            results.append(formatted)
                    else:
                        body = await resp.text()
                        logger.error(f"JustWatch API error: {resp.status} - {body[:500]}")

        except asyncio.TimeoutError:
            logger.error("JustWatch API timeout")
        except Exception as e:
            logger.error(f"JustWatch search error: {e}")

        return results

    async def get_details(self, content_id: str) -> Dict[str, Any]:
        """Get detailed information about content"""
        return {}
