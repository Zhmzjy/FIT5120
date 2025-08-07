"""
Parking Routes for Melbourne Parking API
Updated to use PostgreSQL with Suburb and OffStreetParking models
"""

from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from sqlalchemy import func, text
from ..models import db, Suburb, OffStreetParking, ParkingSpaces, OnStreetSensors

# Create parking routes blueprint
parking_bp = Blueprint('parking', __name__)

@parking_bp.route('/facilities', methods=['GET'])
def get_parking_facilities():
    """
    Get all parking facilities

    Query Parameters:
        suburb (str): Filter by suburb name
        postcode (str): Filter by postcode
        lat (float): Latitude for location-based filtering
        lng (float): Longitude for location-based filtering
        radius (float): Search radius in km (default: 2.0)
        limit (int): Limit number of results (default: 100)
    """
    try:
        query = OffStreetParking.query

        # Filter by suburb
        suburb_filter = request.args.get('suburb')
        if suburb_filter:
            query = query.filter(OffStreetParking.suburb_name.ilike(f'%{suburb_filter}%'))

        # Filter by postcode
        postcode_filter = request.args.get('postcode')
        if postcode_filter:
            query = query.filter(OffStreetParking.postcode == postcode_filter)

        # Location-based filtering
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        radius = request.args.get('radius', default=2.0, type=float)

        if lat and lng:
            # Simple distance calculation (for small distances)
            distance_query = func.sqrt(
                func.power(OffStreetParking.latitude - lat, 2) +
                func.power(OffStreetParking.longitude - lng, 2)
            )
            # Convert to approximate km (rough conversion)
            query = query.filter(distance_query <= radius / 111.0)
            query = query.order_by(distance_query)
        else:
            query = query.order_by(OffStreetParking.parking_spaces.desc())

        # Limit results
        limit = request.args.get('limit', default=100, type=int)
        facilities = query.limit(limit).all()

        return jsonify({
            'status': 'success',
            'count': len(facilities),
            'data': [facility.to_dict() for facility in facilities]
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to fetch parking facilities: {str(e)}'
        }), 500

@parking_bp.route('/facilities/geojson', methods=['GET'])
def get_parking_facilities_geojson():
    """Get parking facilities in GeoJSON format for map display"""
    try:
        query = OffStreetParking.query

        # Apply same filters as regular facilities endpoint
        suburb_filter = request.args.get('suburb')
        if suburb_filter:
            query = query.filter(OffStreetParking.suburb_name.ilike(f'%{suburb_filter}%'))

        postcode_filter = request.args.get('postcode')
        if postcode_filter:
            query = query.filter(OffStreetParking.postcode == postcode_filter)

        facilities = query.all()

        geojson = {
            'type': 'FeatureCollection',
            'features': [facility.to_geojson_feature() for facility in facilities]
        }

        return jsonify(geojson)

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to fetch GeoJSON data: {str(e)}'
        }), 500

@parking_bp.route('/facilities/<int:facility_id>', methods=['GET'])
def get_parking_facility(facility_id):
    """Get specific parking facility details"""
    try:
        facility = OffStreetParking.query.get_or_404(facility_id)

        return jsonify({
            'status': 'success',
            'data': facility.to_dict()
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to fetch facility: {str(e)}'
        }), 500

@parking_bp.route('/suburbs', methods=['GET'])
def get_suburbs():
    """
    Get all suburbs with parking data

    Query Parameters:
        name (str): Filter by suburb name
        postcode (str): Filter by postcode
        with_parking (bool): Only suburbs with parking facilities
    """
    try:
        query = Suburb.query

        # Filter by name
        name_filter = request.args.get('name')
        if name_filter:
            query = query.filter(Suburb.suburb_name.ilike(f'%{name_filter}%'))

        # Filter by postcode
        postcode_filter = request.args.get('postcode')
        if postcode_filter:
            query = query.filter(Suburb.postcode == postcode_filter)

        # Only suburbs with parking facilities
        with_parking = request.args.get('with_parking', type=bool)
        if with_parking:
            query = query.join(OffStreetParking).group_by(Suburb.id)

        suburbs = query.order_by(Suburb.suburb_name).all()

        return jsonify({
            'status': 'success',
            'count': len(suburbs),
            'data': [suburb.to_dict() for suburb in suburbs]
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to fetch suburbs: {str(e)}'
        }), 500

@parking_bp.route('/suburbs/<int:suburb_id>/facilities', methods=['GET'])
def get_suburb_facilities(suburb_id):
    """Get all parking facilities in a specific suburb"""
    try:
        suburb = Suburb.query.get_or_404(suburb_id)
        facilities = OffStreetParking.query.filter_by(suburb_id=suburb_id).all()

        return jsonify({
            'status': 'success',
            'suburb': suburb.to_dict(),
            'facilities_count': len(facilities),
            'facilities': [facility.to_dict() for facility in facilities]
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to fetch suburb facilities: {str(e)}'
        }), 500

@parking_bp.route('/search', methods=['GET'])
def search_parking():
    """
    Search parking facilities by address or name

    Query Parameters:
        q (str): Search query
        limit (int): Limit results (default: 20)
    """
    try:
        search_query = request.args.get('q', '').strip()
        if not search_query:
            return jsonify({
                'status': 'error',
                'message': 'Search query is required'
            }), 400

        limit = request.args.get('limit', default=20, type=int)

        # Search in building address
        facilities = OffStreetParking.query.filter(
            OffStreetParking.building_address.ilike(f'%{search_query}%')
        ).order_by(OffStreetParking.parking_spaces.desc()).limit(limit).all()

        return jsonify({
            'status': 'success',
            'query': search_query,
            'count': len(facilities),
            'data': [facility.to_dict() for facility in facilities]
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Search failed: {str(e)}'
        }), 500

# Legacy endpoint for compatibility
@parking_bp.route('/live', methods=['GET'])
def get_live_parking():
    """
    Legacy endpoint - now returns static parking facilities data
    Kept for backwards compatibility
    """
    try:
        # Get first 50 facilities as "live" data
        facilities = OffStreetParking.query.limit(50).all()

        # Convert to legacy format
        legacy_data = []
        for facility in facilities:
            legacy_data.append({
                'id': facility.id,
                'kerbside_id': facility.id,  # Use facility ID as kerbside_id
                'zone_number': f"ZONE_{facility.id}",
                'status': 'available',  # Default status
                'coordinates': [float(facility.latitude), float(facility.longitude)],
                'latitude': float(facility.latitude),
                'longitude': float(facility.longitude),
                'status_timestamp': datetime.utcnow().isoformat(),
                'last_updated': datetime.utcnow().isoformat(),
                'parking_spaces': facility.parking_spaces,
                'address': facility.building_address
            })

        return jsonify({
            'status': 'success',
            'count': len(legacy_data),
            'data': legacy_data,
            'message': 'Legacy endpoint - showing parking facilities as live data'
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to fetch live parking data: {str(e)}'
        }), 500

@parking_bp.route('/combined', methods=['GET'])
def get_combined_parking():
    """
    Get combined parking data from both on-street sensors and off-street facilities
    
    Query Parameters:
        parking_type (str): Filter by parking type ('on-street', 'off-street', 'all')
        status (str): Filter by status ('available', 'occupied', 'all')
        suburb (str): Filter by suburb name
        zone (int): Filter by zone number
        lat (float): Latitude for location-based filtering
        lng (float): Longitude for location-based filtering
        radius (float): Search radius in km (default: 2.0)
        limit (int): Limit number of results (default: 200)
    """
    try:
        from ..models import OnStreetSensors
        
        parking_type = request.args.get('parking_type', 'all')
        status_filter = request.args.get('status', 'all')
        suburb_filter = request.args.get('suburb')
        zone_filter = request.args.get('zone', type=int)
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        radius = request.args.get('radius', default=2.0, type=float)
        limit = request.args.get('limit', default=200, type=int)
        
        combined_data = []
        
        # Get on-street parking data
        if parking_type in ['all', 'on-street']:
            on_street_query = OnStreetSensors.query
            
            # Apply filters
            if status_filter == 'available':
                on_street_query = on_street_query.filter(OnStreetSensors.status_description == 'Unoccupied')
            elif status_filter == 'occupied':
                on_street_query = on_street_query.filter(OnStreetSensors.status_description == 'Present')
            
            if suburb_filter:
                on_street_query = on_street_query.filter(OnStreetSensors.suburb_name.ilike(f'%{suburb_filter}%'))
            
            if zone_filter:
                on_street_query = on_street_query.filter(OnStreetSensors.zone_number == zone_filter)
            
            # Location-based filtering
            if lat and lng:
                lat_diff = radius / 111.0
                lng_diff = radius / (111.0 * abs(lat) / 90.0)
                on_street_query = on_street_query.filter(
                    OnStreetSensors.latitude.between(lat - lat_diff, lat + lat_diff),
                    OnStreetSensors.longitude.between(lng - lng_diff, lng + lng_diff)
                )
            
            on_street_sensors = on_street_query.limit(limit // 2).all()
            
            # Convert to unified format
            for sensor in on_street_sensors:
                combined_data.append({
                    'id': sensor.id,
                    'kerbside_id': sensor.kerbside_id,
                    'zone_number': sensor.zone_number,
                    'status': 'available' if sensor.status_description == 'Unoccupied' else 'occupied',
                    'parking_type': 'on-street',
                    'coordinates': [float(sensor.latitude), float(sensor.longitude)],
                    'latitude': float(sensor.latitude),
                    'longitude': float(sensor.longitude),
                    'status_timestamp': sensor.status_timestamp.isoformat() if sensor.status_timestamp else None,
                    'last_updated': sensor.last_updated.isoformat() if sensor.last_updated else None,
                    'suburb_name': sensor.suburb_name,
                    'postcode': sensor.postcode,
                    'parking_spaces': 1  # Each sensor represents one parking space
                })
        
        # Get off-street parking data
        if parking_type in ['all', 'off-street']:
            off_street_query = OffStreetParking.query
            
            # Apply filters
            if suburb_filter:
                off_street_query = off_street_query.filter(OffStreetParking.suburb_name.ilike(f'%{suburb_filter}%'))
            
            # Location-based filtering
            if lat and lng:
                lat_diff = radius / 111.0
                lng_diff = radius / (111.0 * abs(lat) / 90.0)
                off_street_query = off_street_query.filter(
                    OffStreetParking.latitude.between(lat - lat_diff, lat + lat_diff),
                    OffStreetParking.longitude.between(lng - lng_diff, lng + lng_diff)
                )
            
            off_street_facilities = off_street_query.limit(limit // 2).all()
            
            # Convert to unified format
            for facility in off_street_facilities:
                combined_data.append({
                    'id': facility.id,
                    'kerbside_id': facility.id,
                    'zone_number': f"FACILITY_{facility.id}",
                    'status': 'available',  # Off-street facilities are generally available
                    'parking_type': 'off-street',
                    'coordinates': [float(facility.latitude), float(facility.longitude)],
                    'latitude': float(facility.latitude),
                    'longitude': float(facility.longitude),
                    'status_timestamp': datetime.utcnow().isoformat(),
                    'last_updated': facility.updated_at.isoformat() if facility.updated_at else datetime.utcnow().isoformat(),
                    'suburb_name': facility.suburb_name,
                    'postcode': facility.postcode,
                    'parking_spaces': facility.parking_spaces,
                    'address': facility.building_address
                })
        
        # Apply final limit and sort by last_updated
        combined_data = sorted(combined_data, key=lambda x: x['last_updated'], reverse=True)[:limit]
        
        return jsonify({
            'success': True,
            'count': len(combined_data),
            'data': combined_data,
            'message': f'Found {len(combined_data)} parking spaces'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to fetch combined parking data: {str(e)}'
        }), 500
