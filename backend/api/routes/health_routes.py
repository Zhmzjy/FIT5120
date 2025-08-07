"""
Health Check Routes for Melbourne Parking API
Updated for PostgreSQL database
"""

from flask import Blueprint, jsonify
from datetime import datetime
from ..models import db, OffStreetParking, Suburb

# Create health routes blueprint
health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
@health_bp.route('/', methods=['GET'])
@health_bp.route('/check', methods=['GET'])
def health_check():
    """
    Basic health check endpoint for PostgreSQL database
    """
    try:
        # Test database connection with our PostgreSQL data
        facility_count = OffStreetParking.query.count()
        suburb_count = Suburb.query.count()

        return jsonify({
            'status': 'healthy',
            'service': 'Melbourne Parking API',
            'version': '2.0.0',
            'database': 'PostgreSQL',
            'timestamp': datetime.utcnow().isoformat(),
            'data': {
                'parking_facilities': facility_count,
                'suburbs': suburb_count,
                'database_status': 'connected'
            }
        })

    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'service': 'Melbourne Parking API',
            'version': '2.0.0',
            'database': 'PostgreSQL',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e),
            'data': {
                'database_status': 'disconnected'
            }
        }), 503

@health_bp.route('/api/health', methods=['GET'])
def api_health_check():
    """
    Detailed API health check with database stats
    """
    try:
        # Get database statistics
        facility_count = OffStreetParking.query.count()
        suburb_count = Suburb.query.count()

        # Get total parking spaces
        total_spaces = db.session.query(db.func.sum(OffStreetParking.parking_spaces)).scalar() or 0

        return jsonify({
            'status': 'healthy',
            'service': 'Melbourne Parking API',
            'version': '2.0.0',
            'database': {
                'type': 'PostgreSQL',
                'status': 'connected',
                'statistics': {
                    'parking_facilities': facility_count,
                    'total_suburbs': suburb_count,
                    'total_parking_spaces': int(total_spaces)
                }
            },
            'endpoints': {
                'facilities': '/api/parking/facilities',
                'suburbs': '/api/parking/suburbs',
                'search': '/api/parking/search',
                'stats': '/api/stats'
            },
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'service': 'Melbourne Parking API',
            'version': '2.0.0',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503
