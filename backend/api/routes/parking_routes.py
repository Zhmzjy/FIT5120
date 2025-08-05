"""
Parking Routes for Melbourne Parking API
"""

from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from ..models import ParkingSensor, db
from ..services import MelbourneParkingService

# Create parking routes blueprint
parking_bp = Blueprint('parking', __name__)

@parking_bp.route('/live', methods=['GET'])
def get_live_parking():
    """
    Get live parking data from sensors

    Query Parameters:
        lat (float): Latitude for location-based filtering
        lng (float): Longitude for location-based filtering
        radius (float): Search radius in km (default: 2.0)
        status (str): Filter by status ('all', 'available', 'occupied')
    """
    try:
        # Get query parameters
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        radius = request.args.get('radius', default=2.0, type=float)
        status_filter = request.args.get('status', default='all')

        query = ParkingSensor.query

        # Filter by status if specified
        if status_filter != 'all':
            if status_filter.lower() == 'available':
                query = query.filter(ParkingSensor.status_description == 'Unoccupied')
            elif status_filter.lower() == 'occupied':
                query = query.filter(ParkingSensor.status_description == 'Occupied')

        # If location provided, filter by radius (simplified distance calculation)
        if lat and lng:
            lat_range = radius / 111.0  # Rough conversion: 1 degree ≈ 111 km
            lng_range = radius / (111.0 * abs(lat / 90.0))  # Adjust for latitude

            query = query.filter(
                ParkingSensor.latitude.between(lat - lat_range, lat + lat_range),
                ParkingSensor.longitude.between(lng - lng_range, lng + lng_range)
            )

        # Get recent data (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(hours=24)
        query = query.filter(ParkingSensor.last_updated >= yesterday)

        sensors = query.limit(200).all()

        return jsonify({
            'success': True,
            'count': len(sensors),
            'data': [sensor.to_dict() for sensor in sensors],
            'filters': {
                'status': status_filter,
                'location': [lat, lng] if lat and lng else None,
                'radius': radius
            },
            'last_updated': datetime.utcnow().isoformat()
        })

    except Exception as e:
        print(f"Error getting live parking data: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'count': 0,
            'data': []
        }), 500

@parking_bp.route('/search', methods=['GET'])
def search_parking():
    """
    Search parking by postcode or suburb name

    Query Parameters:
        q (str): Search query (postcode or suburb name)
        status (str): Filter by status ('all', 'available', 'occupied')
    """
    try:
        query_text = request.args.get('q', '').strip()
        status_filter = request.args.get('status', default='all')

        if not query_text:
            return jsonify({
                'success': False,
                'error': 'Search query parameter "q" is required',
                'count': 0,
                'data': []
            }), 400

        # For MVP, return parking data near Melbourne CBD
        # In full implementation, you'd geocode the search term first
        cbd_lat, cbd_lng = -37.8136, 144.9631

        # Get parking sensors near Melbourne CBD
        lat_range = 0.05  # Roughly 5km radius
        lng_range = 0.05

        query = ParkingSensor.query.filter(
            ParkingSensor.latitude.between(cbd_lat - lat_range, cbd_lat + lat_range),
            ParkingSensor.longitude.between(cbd_lng - lng_range, cbd_lng + lng_range)
        )

        # Apply status filter
        if status_filter != 'all':
            if status_filter.lower() == 'available':
                query = query.filter(ParkingSensor.status_description == 'Unoccupied')
            elif status_filter.lower() == 'occupied':
                query = query.filter(ParkingSensor.status_description == 'Occupied')

        sensors = query.limit(100).all()

        return jsonify({
            'success': True,
            'query': query_text,
            'count': len(sensors),
            'data': [sensor.to_dict() for sensor in sensors],
            'center': [cbd_lat, cbd_lng],
            'search_area': 'Melbourne CBD (5km radius)',
            'status_filter': status_filter
        })

    except Exception as e:
        print(f"Error searching parking: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'count': 0,
            'data': []
        }), 500

@parking_bp.route('/update', methods=['POST'])
def update_parking_data():
    """
    Manually trigger parking data update from Melbourne Government API
    """
    try:
        success = MelbourneParkingService.update_database()

        if success:
            count = ParkingSensor.query.count()
            return jsonify({
                'success': True,
                'message': 'Parking data updated successfully',
                'total_sensors': count,
                'updated_at': datetime.utcnow().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to update parking data from API',
                'message': 'Check logs for detailed error information'
            }), 500

    except Exception as e:
        print(f"Error updating parking data: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Unexpected error during data update'
        }), 500

@parking_bp.route('/zones', methods=['GET'])
def get_parking_zones():
    """
    Get list of all parking zones with basic statistics
    """
    try:
        zones_data = {}
        sensors = ParkingSensor.query.all()

        for sensor in sensors:
            zone = sensor.zone_number or 'Unknown'
            if zone not in zones_data:
                zones_data[zone] = {
                    'zone_number': zone,
                    'total_spaces': 0,
                    'available': 0,
                    'occupied': 0,
                    'sensors': []
                }

            zones_data[zone]['total_spaces'] += 1
            zones_data[zone]['sensors'].append(sensor.kerbside_id)

            if sensor.status_description == 'Unoccupied':
                zones_data[zone]['available'] += 1
            elif sensor.status_description == 'Occupied':
                zones_data[zone]['occupied'] += 1

        # Calculate occupancy rates
        for zone_data in zones_data.values():
            if zone_data['total_spaces'] > 0:
                zone_data['occupancy_rate'] = round(
                    (zone_data['occupied'] / zone_data['total_spaces'] * 100), 2
                )
            else:
                zone_data['occupancy_rate'] = 0

        return jsonify({
            'success': True,
            'zones': list(zones_data.values()),
            'total_zones': len(zones_data),
            'last_updated': datetime.utcnow().isoformat()
        })

    except Exception as e:
        print(f"Error getting parking zones: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'zones': [],
            'total_zones': 0
        }), 500
