"""
Search routes - Query streaming services for content
"""

from flask import Blueprint, request, jsonify

search_bp = Blueprint('search', __name__, url_prefix='/api/search')


@search_bp.route('/all', methods=['GET'])
def search_all():
    """
    Search all streaming services for content
    Query params:
        - query: search term (show name, movie name, sports event)
        - content_type: 'show', 'movie', 'sports' (optional)
    """
    query = request.args.get('query', '')
    content_type = request.args.get('content_type', None)

    if not query:
        return jsonify({'error': 'Query parameter required'}), 400

    # Mock results for demonstration
    mock_results = [
        {
            'id': 'show_1',
            'title': query,
            'type': 'show',
            'poster': 'https://via.placeholder.com/150x225?text=' + query,
            'description': f'Mock search result for {query}',
            'available_services': ['YouTubeTV', 'Peacock', 'HBO Max'],
            'available_tvs': ['big_screen', 'upper_left']
        },
        {
            'id': 'movie_1',
            'title': f'{query} - Movie',
            'type': 'movie',
            'poster': 'https://via.placeholder.com/150x225?text=Movie',
            'description': f'Mock movie result for {query}',
            'available_services': ['Amazon Prime', 'HBO Max'],
            'available_tvs': ['big_screen', 'upper_right', 'lower_left']
        }
    ]

    return jsonify({
        'query': query,
        'content_type': content_type,
        'results': mock_results,
        'total': len(mock_results)
    }), 200


@search_bp.route('/youtube-tv', methods=['GET'])
def search_youtube_tv():
    """Search YouTubeTV for content"""
    query = request.args.get('query', '')
    if not query:
        return jsonify({'error': 'Query required'}), 400

    # TODO: Implement actual YouTubeTV API call
    return jsonify({
        'service': 'YouTubeTV',
        'results': []
    }), 200


@search_bp.route('/peacock', methods=['GET'])
def search_peacock():
    """Search Peacock for content"""
    query = request.args.get('query', '')
    if not query:
        return jsonify({'error': 'Query required'}), 400

    # TODO: Implement actual Peacock API call
    return jsonify({
        'service': 'Peacock',
        'results': []
    }), 200


@search_bp.route('/espn-plus', methods=['GET'])
def search_espn_plus():
    """Search ESPN+ for sports content"""
    query = request.args.get('query', '')
    if not query:
        return jsonify({'error': 'Query required'}), 400

    # TODO: Implement actual ESPN+ API call
    return jsonify({
        'service': 'ESPN+',
        'results': []
    }), 200


@search_bp.route('/amazon-prime', methods=['GET'])
def search_amazon_prime():
    """Search Amazon Prime Video for content"""
    query = request.args.get('query', '')
    if not query:
        return jsonify({'error': 'Query required'}), 400

    # TODO: Implement actual Prime Video API call
    return jsonify({
        'service': 'Amazon Prime',
        'results': []
    }), 200


@search_bp.route('/hbo-max', methods=['GET'])
def search_hbo_max():
    """Search HBO Max for content"""
    query = request.args.get('query', '')
    if not query:
        return jsonify({'error': 'Query required'}), 400

    # TODO: Implement actual HBO Max API call
    return jsonify({
        'service': 'HBO Max',
        'results': []
    }), 200
