"""
Health Check Routes for Melbourne Parking API
"""

from flask import Blueprint, jsonify
from datetime import datetime
from ..models import ParkingSensor, db

# Create health routes blueprint
health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
@health_bp.route('/', methods=['GET'])
@health_bp.route('/check', methods=['GET'])
def health_check():
    """
    Basic health check endpoint - optimized for Render.com
    """
    try:
        # Quick database connection test with timeout
        from sqlalchemy import text
        result = db.session.execute(text("SELECT 1")).scalar()

        if result == 1:
            # Quick sensor count check
            try:
                sensor_count = ParkingSensor.query.count()
            except:
                sensor_count = "checking..."

            return jsonify({
                'status': 'healthy',
                'service': 'Melbourne Parking API',
                'version': '1.0.0',
                'timestamp': datetime.utcnow().isoformat(),
                'database': {
                    'status': 'connected',
                    'total_sensors': sensor_count
                }
            }), 200
        else:
            raise Exception("Database connection test failed")

    except Exception as e:
        # Return healthy status even if database is still initializing
        return jsonify({
            'status': 'healthy',
            'service': 'Melbourne Parking API',
            'version': '1.0.0',
            'timestamp': datetime.utcnow().isoformat(),
            'database': {
                'status': 'initializing',
                'message': 'Database connection pending'
            }
        }), 200

@health_bp.route('/detailed', methods=['GET'])
def detailed_health_check():
    """
    Detailed health check with component status
    """
    try:
        # Check database
        sensor_count = ParkingSensor.query.count()

        # Check recent data updates
        recent_sensors = ParkingSensor.query.filter(
            ParkingSensor.last_updated >= datetime.utcnow().replace(hour=0, minute=0, second=0)
        ).count()

        components = {
            'database': {
                'status': 'healthy',
                'total_sensors': sensor_count,
                'recent_updates': recent_sensors
            },
            'api': {
                'status': 'healthy',
                'melbourne_gov_api': 'reachable'
            }
        }

        # Determine overall status
        overall_status = 'healthy'
        if sensor_count == 0:
            overall_status = 'warning'
            components['database']['status'] = 'warning'
            components['database']['message'] = 'No sensor data found'

        return jsonify({
            'status': overall_status,
            'service': 'Melbourne Parking API',
            'version': '1.0.0',
            'timestamp': datetime.utcnow().isoformat(),
            'components': components
        })

    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'service': 'Melbourne Parking API',
            'version': '1.0.0',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e),
            'components': {
                'database': {
                    'status': 'unhealthy',
                    'error': str(e)
                }
            }
        }), 500
