"""
On-Street Sensors Routes for Melbourne Parking API
Handles real-time parking sensor data
"""

from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from sqlalchemy import func
from ..models import db, OnStreetSensors

# Create sensors routes blueprint
sensors_bp = Blueprint('sensors', __name__)

@sensors_bp.route('/sensors', methods=['GET'])
def get_sensors():
    """
    Get all parking sensors
    
    Query Parameters:
        status (str): Filter by status (Present, Unoccupied, etc.)
        suburb (str): Filter by suburb name
        zone (int): Filter by zone number
        lat (float): Latitude for location-based filtering
        lng (float): Longitude for location-based filtering
        radius (float): Search radius in km (default: 2.0)
        active_hours (int): Only show sensors updated within X hours (default: 24)
        limit (int): Limit number of results (default: 100)
    """
    try:
        query = OnStreetSensors.query
        
        # Filter by status
        status_filter = request.args.get('status')
        if status_filter:
            query = query.filter(OnStreetSensors.status_description == status_filter)
        
        # Filter by suburb
        suburb_filter = request.args.get('suburb')
        if suburb_filter:
            query = query.filter(OnStreetSensors.suburb_name.ilike(f'%{suburb_filter}%'))
        
        # Filter by zone
        zone_filter = request.args.get('zone', type=int)
        if zone_filter:
            query = query.filter(OnStreetSensors.zone_number == zone_filter)
        
        # Filter by active hours
        active_hours = request.args.get('active_hours', default=24, type=int)
        cutoff_time = datetime.utcnow() - timedelta(hours=active_hours)
        query = query.filter(OnStreetSensors.last_updated >= cutoff_time)
        
        # Location-based filtering
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        radius = request.args.get('radius', default=2.0, type=float)
        
        if lat and lng:
            # Simple distance calculation (for small distances)
            lat_diff = radius / 111.0
            lng_diff = radius / (111.0 * abs(lat) / 90.0)
            
            query = query.filter(
                OnStreetSensors.latitude.between(lat - lat_diff, lat + lat_diff),
                OnStreetSensors.longitude.between(lng - lng_diff, lng + lng_diff)
            )
        
        # Order by last updated (most recent first)
        query = query.order_by(OnStreetSensors.last_updated.desc())
        
        # Limit results
        limit = request.args.get('limit', default=100, type=int)
        sensors = query.limit(limit).all()
        
        return jsonify({
            'status': 'success',
            'count': len(sensors),
            'data': [sensor.to_dict() for sensor in sensors]
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to fetch sensors: {str(e)}'
        }), 500

@sensors_bp.route('/sensors/geojson', methods=['GET'])
def get_sensors_geojson():
    """
    Get parking sensors in GeoJSON format for mapping
    
    Query Parameters:
        status (str): Filter by status
        suburb (str): Filter by suburb name
        zone (int): Filter by zone number
        active_hours (int): Only show sensors updated within X hours
        limit (int): Limit number of results
    """
    try:
        query = OnStreetSensors.query
        
        # Apply same filters as get_sensors
        status_filter = request.args.get('status')
        if status_filter:
            query = query.filter(OnStreetSensors.status_description == status_filter)
        
        suburb_filter = request.args.get('suburb')
        if suburb_filter:
            query = query.filter(OnStreetSensors.suburb_name.ilike(f'%{suburb_filter}%'))
        
        zone_filter = request.args.get('zone', type=int)
        if zone_filter:
            query = query.filter(OnStreetSensors.zone_number == zone_filter)
        
        active_hours = request.args.get('active_hours', default=24, type=int)
        cutoff_time = datetime.utcnow() - timedelta(hours=active_hours)
        query = query.filter(OnStreetSensors.last_updated >= cutoff_time)
        
        # Limit results
        limit = request.args.get('limit', default=1000, type=int)
        sensors = query.limit(limit).all()
        
        # Convert to GeoJSON
        features = [sensor.to_geojson() for sensor in sensors]
        
        geojson = {
            'type': 'FeatureCollection',
            'features': features
        }
        
        return jsonify(geojson)
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to fetch sensors GeoJSON: {str(e)}'
        }), 500

@sensors_bp.route('/sensors/<int:kerbside_id>', methods=['GET'])
def get_sensor_by_id(kerbside_id):
    """
    Get a specific sensor by kerbside ID
    """
    try:
        sensor = OnStreetSensors.query.filter_by(kerbside_id=kerbside_id).first()
        
        if not sensor:
            return jsonify({
                'status': 'error',
                'message': f'Sensor with kerbside_id {kerbside_id} not found'
            }), 404
        
        return jsonify({
            'status': 'success',
            'data': sensor.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to fetch sensor: {str(e)}'
        }), 500

@sensors_bp.route('/sensors/stats', methods=['GET'])
def get_sensor_statistics():
    """
    Get sensor statistics
    
    Query Parameters:
        suburb (str): Filter statistics by suburb
        zone (int): Filter statistics by zone
    """
    try:
        suburb_filter = request.args.get('suburb')
        zone_filter = request.args.get('zone', type=int)
        
        query = OnStreetSensors.query
        
        if suburb_filter:
            query = query.filter(OnStreetSensors.suburb_name.ilike(f'%{suburb_filter}%'))
        
        if zone_filter:
            query = query.filter(OnStreetSensors.zone_number == zone_filter)
        
        # Get counts
        total = query.count()
        occupied = query.filter(OnStreetSensors.status_description == 'Present').count()
        available = query.filter(OnStreetSensors.status_description == 'Unoccupied').count()
        
        # Calculate occupancy rate
        occupancy_rate = round((occupied / total * 100), 2) if total > 0 else 0
        
        # Get recent activity (last 24 hours)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        recent_updates = query.filter(OnStreetSensors.last_updated >= cutoff_time).count()
        
        stats = {
            'total_sensors': total,
            'occupied_sensors': occupied,
            'available_sensors': available,
            'occupancy_rate': occupancy_rate,
            'recent_updates_24h': recent_updates,
            'last_updated': datetime.utcnow().isoformat()
        }
        
        return jsonify({
            'status': 'success',
            'data': stats
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to fetch statistics: {str(e)}'
        }), 500

@sensors_bp.route('/sensors/zones', methods=['GET'])
def get_sensor_zones():
    """
    Get unique zone numbers and their statistics
    """
    try:
        # Get unique zones with counts
        zones = db.session.query(
            OnStreetSensors.zone_number,
            func.count(OnStreetSensors.id).label('total_sensors'),
            func.count(func.case([(OnStreetSensors.status_description == 'Present', 1)])).label('occupied'),
            func.count(func.case([(OnStreetSensors.status_description == 'Unoccupied', 1)])).label('available')
        ).filter(
            OnStreetSensors.zone_number.isnot(None)
        ).group_by(
            OnStreetSensors.zone_number
        ).order_by(
            OnStreetSensors.zone_number
        ).all()
        
        zone_data = []
        for zone in zones:
            occupancy_rate = round((zone.occupied / zone.total_sensors * 100), 2) if zone.total_sensors > 0 else 0
            zone_data.append({
                'zone_number': zone.zone_number,
                'total_sensors': zone.total_sensors,
                'occupied_sensors': zone.occupied,
                'available_sensors': zone.available,
                'occupancy_rate': occupancy_rate
            })
        
        return jsonify({
            'status': 'success',
            'count': len(zone_data),
            'data': zone_data
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to fetch zones: {str(e)}'
        }), 500

@sensors_bp.route('/sensors/suburbs', methods=['GET'])
def get_sensor_suburbs():
    """
    Get unique suburbs and their sensor statistics
    """
    try:
        # Get unique suburbs with counts
        suburbs = db.session.query(
            OnStreetSensors.suburb_name,
            func.count(OnStreetSensors.id).label('total_sensors'),
            func.count(func.case([(OnStreetSensors.status_description == 'Present', 1)])).label('occupied'),
            func.count(func.case([(OnStreetSensors.status_description == 'Unoccupied', 1)])).label('available')
        ).filter(
            OnStreetSensors.suburb_name.isnot(None)
        ).group_by(
            OnStreetSensors.suburb_name
        ).order_by(
            func.count(OnStreetSensors.id).desc()
        ).all()
        
        suburb_data = []
        for suburb in suburbs:
            occupancy_rate = round((suburb.occupied / suburb.total_sensors * 100), 2) if suburb.total_sensors > 0 else 0
            suburb_data.append({
                'suburb_name': suburb.suburb_name,
                'total_sensors': suburb.total_sensors,
                'occupied_sensors': suburb.occupied,
                'available_sensors': suburb.available,
                'occupancy_rate': occupancy_rate
            })
        
        return jsonify({
            'status': 'success',
            'count': len(suburb_data),
            'data': suburb_data
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to fetch suburbs: {str(e)}'
        }), 500

