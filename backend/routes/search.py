"""
Search routes - Query streaming services for content
Implements unified search across all streaming services
"""

import asyncio
import sys
import os
from flask import Blueprint, request, jsonify

# Ensure correct Python path for imports
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from apis.search import get_search_aggregator

search_bp = Blueprint('search', __name__, url_prefix='/api/search')


@search_bp.route('/all', methods=['GET'])
def search_all():
    """
    Search all streaming services for content
    Query params:
        - query: search term (show name, movie name, sports event)
        - content_type: 'show', 'movie', 'sports' (optional, defaults to 'all')
    """
    query = request.args.get('query', '').strip()
    content_type = request.args.get('content_type', 'all').lower()

    if not query:
        return jsonify({'error': 'Query parameter required'}), 400

    # Validate content_type
    if content_type not in ['all', 'show', 'movie', 'sports']:
        return jsonify({'error': 'Invalid content_type. Use: all, show, movie, or sports'}), 400

    try:
        # Get search aggregator
        aggregator = get_search_aggregator()

        # Run async search - handle event loop properly for Flask
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError("Event loop is closed")
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        result = loop.run_until_complete(aggregator.search(query, content_type))

        return jsonify(result), 200

    except Exception as e:
        print(f"Error during search: {e}")
        return jsonify({
            'error': 'Search failed',
            'message': str(e)
        }), 500


@search_bp.route('/youtube-tv', methods=['GET'])
def search_youtube_tv():
    """Search YouTubeTV for content"""
    query = request.args.get('query', '').strip()
    content_type = request.args.get('content_type', 'all').lower()

    if not query:
        return jsonify({'error': 'Query required'}), 400

    try:
        from apis.streaming.youtube_tv import YouTubeTVProvider

        provider = YouTubeTVProvider()
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(provider.search(query, content_type))

        return jsonify({
            'service': 'YouTubeTV',
            'query': query,
            'results': results,
            'total': len(results)
        }), 200

    except Exception as e:
        print(f"Error searching YouTubeTV: {e}")
        return jsonify({'error': 'Search failed', 'message': str(e)}), 500


@search_bp.route('/peacock', methods=['GET'])
def search_peacock():
    """Search Peacock for content"""
    query = request.args.get('query', '').strip()
    content_type = request.args.get('content_type', 'all').lower()

    if not query:
        return jsonify({'error': 'Query required'}), 400

    try:
        from apis.streaming.peacock import PeacockProvider

        provider = PeacockProvider()
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(provider.search(query, content_type))

        return jsonify({
            'service': 'Peacock',
            'query': query,
            'results': results,
            'total': len(results)
        }), 200

    except Exception as e:
        print(f"Error searching Peacock: {e}")
        return jsonify({'error': 'Search failed', 'message': str(e)}), 500


@search_bp.route('/espn-plus', methods=['GET'])
def search_espn_plus():
    """Search ESPN+ for sports content"""
    query = request.args.get('query', '').strip()
    content_type = request.args.get('content_type', 'all').lower()

    if not query:
        return jsonify({'error': 'Query required'}), 400

    try:
        from apis.streaming.espn_plus import ESPNPlusProvider

        provider = ESPNPlusProvider()
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(provider.search(query, content_type))

        return jsonify({
            'service': 'ESPN+',
            'query': query,
            'results': results,
            'total': len(results)
        }), 200

    except Exception as e:
        print(f"Error searching ESPN+: {e}")
        return jsonify({'error': 'Search failed', 'message': str(e)}), 500


@search_bp.route('/amazon-prime', methods=['GET'])
def search_amazon_prime():
    """Search Amazon Prime Video for content"""
    query = request.args.get('query', '').strip()
    content_type = request.args.get('content_type', 'all').lower()

    if not query:
        return jsonify({'error': 'Query required'}), 400

    try:
        from apis.streaming.prime_video import PrimeVideoProvider

        provider = PrimeVideoProvider()
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(provider.search(query, content_type))

        return jsonify({
            'service': 'Amazon Prime',
            'query': query,
            'results': results,
            'total': len(results)
        }), 200

    except Exception as e:
        print(f"Error searching Amazon Prime: {e}")
        return jsonify({'error': 'Search failed', 'message': str(e)}), 500


@search_bp.route('/hbo-max', methods=['GET'])
def search_hbo_max():
    """Search HBO Max for content"""
    query = request.args.get('query', '').strip()
    content_type = request.args.get('content_type', 'all').lower()

    if not query:
        return jsonify({'error': 'Query required'}), 400

    try:
        from apis.streaming.hbo_max import HBOMaxProvider

        provider = HBOMaxProvider()
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(provider.search(query, content_type))

        return jsonify({
            'service': 'HBO Max',
            'query': query,
            'results': results,
            'total': len(results)
        }), 200

    except Exception as e:
        print(f"Error searching HBO Max: {e}")
        return jsonify({'error': 'Search failed', 'message': str(e)}), 500


@search_bp.route('/youtube', methods=['GET'])
def search_youtube():
    """Search YouTube for content"""
    query = request.args.get('query', '').strip()
    content_type = request.args.get('content_type', 'all').lower()

    if not query:
        return jsonify({'error': 'Query required'}), 400

    try:
        from apis.streaming.youtube import YouTubeProvider

        provider = YouTubeProvider()
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(provider.search(query, content_type))

        return jsonify({
            'service': 'YouTube',
            'query': query,
            'results': results,
            'total': len(results)
        }), 200

    except Exception as e:
        print(f"Error searching YouTube: {e}")
        return jsonify({'error': 'Search failed', 'message': str(e)}), 500


@search_bp.route('/fubo', methods=['GET'])
def search_fubo():
    """Search Fubo for content"""
    query = request.args.get('query', '').strip()
    content_type = request.args.get('content_type', 'all').lower()

    if not query:
        return jsonify({'error': 'Query required'}), 400

    try:
        from apis.streaming.fubo import FuboProvider

        provider = FuboProvider()
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(provider.search(query, content_type))

        return jsonify({
            'service': 'Fubo',
            'query': query,
            'results': results,
            'total': len(results)
        }), 200

    except Exception as e:
        print(f"Error searching Fubo: {e}")
        return jsonify({'error': 'Search failed', 'message': str(e)}), 500


@search_bp.route('/fandango', methods=['GET'])
def search_fandango():
    """Search Fandango for content"""
    query = request.args.get('query', '').strip()
    content_type = request.args.get('content_type', 'all').lower()

    if not query:
        return jsonify({'error': 'Query required'}), 400

    try:
        from apis.streaming.fandango import FandangoProvider

        provider = FandangoProvider()
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(provider.search(query, content_type))

        return jsonify({
            'service': 'Fandango',
            'query': query,
            'results': results,
            'total': len(results)
        }), 200

    except Exception as e:
        print(f"Error searching Fandango: {e}")
        return jsonify({'error': 'Search failed', 'message': str(e)}), 500


@search_bp.route('/cache-stats', methods=['GET'])
def get_cache_stats():
    """Get search cache statistics"""
    try:
        aggregator = get_search_aggregator()
        stats = aggregator.get_cache_stats()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': 'Failed to get cache stats', 'message': str(e)}), 500


@search_bp.route('/clear-cache', methods=['POST'])
def clear_cache():
    """Clear the search cache"""
    try:
        aggregator = get_search_aggregator()
        aggregator.clear_cache()
        return jsonify({'message': 'Cache cleared successfully'}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to clear cache', 'message': str(e)}), 500
