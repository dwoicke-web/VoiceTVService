"""
API routes for debug logging dashboard.

Endpoints:
    GET /api/logs/runs - List recent runs
    GET /api/logs/runs/{run_id} - Get full run details
    GET /api/logs/runs/{run_id}/screenshots/{screenshot_id} - Get screenshot
"""

from flask import Blueprint, jsonify, send_file, request
import io

from debug_logging import run_storage

logs_bp = Blueprint('logs', __name__, url_prefix='/api/logs')


@logs_bp.route('/runs', methods=['GET'])
def list_runs():
    """List recent debug runs."""
    try:
        limit = request.args.get('limit', default=50, type=int)
        runs = run_storage.list_runs(limit=min(limit, 100))  # Cap at 100
        return jsonify({
            'runs': runs,
            'count': len(runs),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@logs_bp.route('/runs/<run_id>', methods=['GET'])
def get_run(run_id):
    """Get full details for a run."""
    try:
        run = run_storage.load_run(run_id)
        if not run:
            return jsonify({'error': f'Run {run_id} not found'}), 404

        return jsonify(run)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@logs_bp.route('/runs/<run_id>/screenshots/<screenshot_id>', methods=['GET'])
def get_screenshot(run_id, screenshot_id):
    """Get a screenshot image."""
    try:
        screenshot_data = run_storage.get_screenshot(run_id, screenshot_id)
        if not screenshot_data:
            return jsonify({'error': 'Screenshot not found'}), 404

        return send_file(
            io.BytesIO(screenshot_data),
            mimetype='image/png',
            as_attachment=False,
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@logs_bp.route('/runs/<run_id>', methods=['DELETE'])
def delete_run(run_id):
    """Delete a run."""
    try:
        success = run_storage.delete_run(run_id)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to delete run'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
