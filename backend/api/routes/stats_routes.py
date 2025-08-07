"""
Statistics Routes for Melbourne Parking API
Updated to use PostgreSQL data
"""

from flask import Blueprint, jsonify
from datetime import datetime
from sqlalchemy import func
from ..models import db, Suburb, OffStreetParking

# Create stats routes blueprint
stats_bp = Blueprint('stats', __name__)

@stats_bp.route('/', methods=['GET'])
@stats_bp.route('/overview', methods=['GET'])
def get_stats_overview():
    """
    Get overall parking statistics and overview
    """
    try:
        from ..models import OnStreetSensors
        
        # Off-street parking statistics
        total_facilities = OffStreetParking.query.count()
        total_off_street_spaces = db.session.query(func.sum(OffStreetParking.parking_spaces)).scalar() or 0
        
        # On-street parking statistics
        total_sensors = OnStreetSensors.query.count()
        available_sensors = OnStreetSensors.query.filter(OnStreetSensors.status_description == 'Unoccupied').count()
        occupied_sensors = OnStreetSensors.query.filter(OnStreetSensors.status_description == 'Present').count()
        
        # Combined statistics
        total_parking_spaces = int(total_off_street_spaces) + total_sensors
        total_suburbs_with_parking = db.session.query(func.count(func.distinct(OffStreetParking.suburb_id))).scalar() or 0
        
        # Calculate occupancy rates
        on_street_occupancy_rate = round((occupied_sensors / total_sensors * 100), 2) if total_sensors > 0 else 0
        
        # Top suburbs by parking spaces
        top_suburbs = db.session.query(
            OffStreetParking.suburb_name,
            func.count(OffStreetParking.id).label('facility_count'),
            func.sum(OffStreetParking.parking_spaces).label('total_spaces')
        ).filter(
            OffStreetParking.suburb_name.isnot(None)
        ).group_by(
            OffStreetParking.suburb_name
        ).order_by(
            func.sum(OffStreetParking.parking_spaces).desc()
        ).limit(5).all()

        stats = {
            'total_facilities': total_facilities,
            'total_sensors': total_sensors,
            'total_parking_spaces': total_parking_spaces,
            'off_street_spaces': int(total_off_street_spaces),
            'on_street_spaces': total_sensors,
            'available_sensors': available_sensors,
            'occupied_sensors': occupied_sensors,
            'on_street_occupancy_rate': on_street_occupancy_rate,
            'suburbs_with_parking': total_suburbs_with_parking,
            'top_suburbs': [
                {
                    'suburb_name': row.suburb_name,
                    'facility_count': row.facility_count,
                    'total_spaces': row.total_spaces
                }
                for row in top_suburbs
            ]
        }

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
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@stats_bp.route('/suburbs', methods=['GET'])
def get_suburb_stats():
    """
    Get detailed statistics for each suburb
    """
    try:
        suburb_stats = db.session.query(
            Suburb.id,
            Suburb.suburb_name,
            Suburb.postcode,
            func.count(OffStreetParking.id).label('facility_count'),
            func.coalesce(func.sum(OffStreetParking.parking_spaces), 0).label('total_spaces'),
            func.coalesce(func.avg(OffStreetParking.parking_spaces), 0).label('avg_spaces'),
            func.coalesce(func.min(OffStreetParking.parking_spaces), 0).label('min_spaces'),
            func.coalesce(func.max(OffStreetParking.parking_spaces), 0).label('max_spaces')
        ).outerjoin(
            OffStreetParking, Suburb.id == OffStreetParking.suburb_id
        ).group_by(
            Suburb.id, Suburb.suburb_name, Suburb.postcode
        ).having(
            func.count(OffStreetParking.id) > 0
        ).order_by(
            func.sum(OffStreetParking.parking_spaces).desc()
        ).all()

        stats_data = []
        for row in suburb_stats:
            stats_data.append({
                'suburb_id': row.id,
                'suburb_name': row.suburb_name,
                'postcode': row.postcode,
                'facility_count': row.facility_count,
                'total_spaces': row.total_spaces,
                'average_spaces': round(float(row.avg_spaces), 1),
                'min_spaces': row.min_spaces,
                'max_spaces': row.max_spaces
            })

        return jsonify({
            'success': True,
            'count': len(stats_data),
            'data': stats_data,
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        print(f"Error getting suburb stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@stats_bp.route('/facilities/distribution', methods=['GET'])
def get_facility_distribution():
    """
    Get distribution of parking facilities by size ranges
    """
    try:
        # Define size ranges
        size_ranges = [
            (0, 50, 'Small (0-50 spaces)'),
            (51, 200, 'Medium (51-200 spaces)'),
            (201, 500, 'Large (201-500 spaces)'),
            (501, 1000, 'Very Large (501-1000 spaces)'),
            (1001, 5000, 'Mega (1000+ spaces)')
        ]

        distribution = []
        for min_size, max_size, label in size_ranges:
            if max_size == 5000:  # For the last range, use >= instead of between
                count = OffStreetParking.query.filter(
                    OffStreetParking.parking_spaces >= min_size
                ).count()
            else:
                count = OffStreetParking.query.filter(
                    OffStreetParking.parking_spaces.between(min_size, max_size)
                ).count()

            distribution.append({
                'range': label,
                'min_spaces': min_size,
                'max_spaces': max_size if max_size != 5000 else None,
                'facility_count': count
            })

        return jsonify({
            'success': True,
            'distribution': distribution,
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        print(f"Error getting facility distribution: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500
