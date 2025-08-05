"""
Statistics Routes for Melbourne Parking API
"""

from flask import Blueprint, jsonify
from datetime import datetime
from ..services import StatsService

# Create stats routes blueprint
stats_bp = Blueprint('stats', __name__)

@stats_bp.route('/', methods=['GET'])
@stats_bp.route('/overview', methods=['GET'])
def get_stats_overview():
    """
    Get overall parking statistics and overview
    """
    try:
        stats = StatsService.get_parking_overview()

        return jsonify({
            'success': True,
            'stats': stats,
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        print(f"Error getting stats overview: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'stats': {}
        }), 500

@stats_bp.route('/zones', methods=['GET'])
def get_zone_stats():
    """
    Get parking statistics by zone
    """
    try:
        zone_stats = StatsService.get_zone_statistics()

        return jsonify({
            'success': True,
            'zone_statistics': zone_stats,
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        print(f"Error getting zone stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'zone_statistics': {}
        }), 500

@stats_bp.route('/parking-lots', methods=['GET'])
def get_parking_lots_stats():
    """
    Get parking lot statistics and information
    """
    try:
        lots_stats = StatsService.get_parking_lots_stats()

        return jsonify({
            'success': True,
            'parking_lots': lots_stats,
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        print(f"Error getting parking lots stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'parking_lots': {}
        }), 500
