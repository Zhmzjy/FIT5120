"""
Parking Restrictions Routes for Melbourne Parking API
Handles pay-stay parking restrictions data
"""

from flask import Blueprint, jsonify, request
from datetime import datetime, time
from sqlalchemy import func
from ..models import db, ParkingRestrictions

# Create restrictions routes blueprint
restrictions_bp = Blueprint('restrictions', __name__)

@restrictions_bp.route('/zones', methods=['GET'])
def get_parking_zones():
    """
    Get all unique parking zones with their restrictions
    
    Query Parameters:
        day_of_week (str): Filter by day of week (1-7)
        active_now (bool): Filter zones active at current time
        min_cost (int): Minimum cost per hour in cents
        max_cost (int): Maximum cost per hour in cents
        limit (int): Limit number of results (default: 100)
    """
    try:
        query = db.session.query(ParkingRestrictions.pay_stay_zone).distinct()
        
        # Filter by day of week
        day_filter = request.args.get('day_of_week')
        if day_filter:
            query = query.filter(ParkingRestrictions.day_of_week == day_filter)
        
        # Filter by cost range
        min_cost = request.args.get('min_cost', type=int)
        if min_cost is not None:
            query = query.filter(ParkingRestrictions.cost_per_hour >= min_cost)
        
        max_cost = request.args.get('max_cost', type=int)
        if max_cost is not None:
            query = query.filter(ParkingRestrictions.cost_per_hour <= max_cost)
        
        # Filter active now
        active_now = request.args.get('active_now', type=bool)
        if active_now:
            now = datetime.now()
            current_time = now.time()
            current_day = str(now.isoweekday())
            query = query.filter(
                ParkingRestrictions.day_of_week == current_day,
                ParkingRestrictions.start_time <= current_time,
                ParkingRestrictions.end_time >= current_time
            )
        
        # Limit results
        limit = request.args.get('limit', default=100, type=int)
        zones = query.limit(limit).all()
        
        zone_list = [zone[0] for zone in zones]
        
        return jsonify({
            'status': 'success',
            'count': len(zone_list),
            'data': zone_list
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to fetch parking zones: {str(e)}'
        }), 500

@restrictions_bp.route('/zones/<int:zone_id>', methods=['GET'])
def get_zone_restrictions(zone_id):
    """
    Get all restrictions for a specific parking zone
    
    Path Parameters:
        zone_id (int): Parking zone identifier
    """
    try:
        restrictions = ParkingRestrictions.get_zone_restrictions(zone_id)
        
        if not restrictions:
            return jsonify({
                'status': 'error',
                'message': f'No restrictions found for zone {zone_id}'
            }), 404
        
        # Get zone summary
        summary = ParkingRestrictions.get_zone_summary(zone_id)
        
        return jsonify({
            'status': 'success',
            'zone_id': zone_id,
            'summary': summary,
            'restrictions': [restriction.to_dict() for restriction in restrictions]
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to fetch zone restrictions: {str(e)}'
        }), 500

@restrictions_bp.route('/day/<day_of_week>', methods=['GET'])
def get_day_restrictions(day_of_week):
    """
    Get all restrictions for a specific day of the week
    
    Path Parameters:
        day_of_week (str): Day of week (1-7, where 1=Monday, 7=Sunday)
    
    Query Parameters:
        min_cost (int): Minimum cost per hour in cents
        max_cost (int): Maximum cost per hour in cents
        limit (int): Limit number of results (default: 100)
    """
    try:
        # Validate day of week
        if day_of_week not in ['1', '2', '3', '4', '5', '6', '7']:
            return jsonify({
                'status': 'error',
                'message': 'Invalid day_of_week. Must be 1-7 (Monday=1, Sunday=7)'
            }), 400
        
        query = ParkingRestrictions.query.filter_by(day_of_week=day_of_week)
        
        # Filter by cost range
        min_cost = request.args.get('min_cost', type=int)
        if min_cost is not None:
            query = query.filter(ParkingRestrictions.cost_per_hour >= min_cost)
        
        max_cost = request.args.get('max_cost', type=int)
        if max_cost is not None:
            query = query.filter(ParkingRestrictions.cost_per_hour <= max_cost)
        
        # Limit results
        limit = request.args.get('limit', default=100, type=int)
        restrictions = query.limit(limit).all()
        
        return jsonify({
            'status': 'success',
            'day_of_week': day_of_week,
            'count': len(restrictions),
            'restrictions': [restriction.to_dict() for restriction in restrictions]
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to fetch day restrictions: {str(e)}'
        }), 500

@restrictions_bp.route('/active', methods=['GET'])
def get_active_restrictions():
    """
    Get currently active restrictions
    
    Query Parameters:
        time (str): Time in HH:MM format (default: current time)
        day_of_week (str): Day of week (1-7, default: current day)
        min_cost (int): Minimum cost per hour in cents
        max_cost (int): Maximum cost per hour in cents
        limit (int): Limit number of results (default: 100)
    """
    try:
        # Get current time and day if not provided
        time_str = request.args.get('time')
        day_of_week = request.args.get('day_of_week')
        
        if time_str:
            try:
                current_time = datetime.strptime(time_str, '%H:%M').time()
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid time format. Use HH:MM (e.g., 09:30)'
                }), 400
        else:
            current_time = datetime.now().time()
        
        if day_of_week:
            if day_of_week not in ['1', '2', '3', '4', '5', '6', '7']:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid day_of_week. Must be 1-7 (Monday=1, Sunday=7)'
                }), 400
        else:
            day_of_week = str(datetime.now().isoweekday())
        
        # Get active restrictions
        restrictions = ParkingRestrictions.get_active_restrictions(current_time, day_of_week)
        
        # Apply cost filters
        min_cost = request.args.get('min_cost', type=int)
        if min_cost is not None:
            restrictions = [r for r in restrictions if r.cost_per_hour >= min_cost]
        
        max_cost = request.args.get('max_cost', type=int)
        if max_cost is not None:
            restrictions = [r for r in restrictions if r.cost_per_hour <= max_cost]
        
        # Limit results
        limit = request.args.get('limit', default=100, type=int)
        restrictions = restrictions[:limit]
        
        return jsonify({
            'status': 'success',
            'check_time': current_time.strftime('%H:%M'),
            'day_of_week': day_of_week,
            'count': len(restrictions),
            'restrictions': [restriction.to_dict() for restriction in restrictions]
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to fetch active restrictions: {str(e)}'
        }), 500

@restrictions_bp.route('/statistics', methods=['GET'])
def get_restrictions_statistics():
    """
    Get overall statistics for parking restrictions
    
    Query Parameters:
        type (str): Type of statistics ('overall', 'daily', 'cost')
    """
    try:
        stats_type = request.args.get('type', 'overall')
        
        if stats_type == 'overall':
            # Overall statistics
            cost_stats = ParkingRestrictions.get_cost_statistics()
            
            # Get total unique zones
            total_zones = db.session.query(func.count(func.distinct(ParkingRestrictions.pay_stay_zone))).scalar()
            
            return jsonify({
                'status': 'success',
                'statistics': {
                    'total_restrictions': cost_stats['total_restrictions'],
                    'total_zones': total_zones,
                    'cost_range': {
                        'min_cents': cost_stats['min_cost_cents'],
                        'max_cents': cost_stats['max_cost_cents'],
                        'avg_cents': cost_stats['avg_cost_cents'],
                        'min_dollars': round(cost_stats['min_cost_cents'] / 100.0, 2),
                        'max_dollars': round(cost_stats['max_cost_cents'] / 100.0, 2),
                        'avg_dollars': round(cost_stats['avg_cost_cents'] / 100.0, 2)
                    }
                }
            })
        
        elif stats_type == 'daily':
            # Daily statistics
            daily_stats = ParkingRestrictions.get_day_statistics()
            
            return jsonify({
                'status': 'success',
                'statistics': daily_stats
            })
        
        elif stats_type == 'cost':
            # Cost distribution
            cost_distribution = db.session.query(
                ParkingRestrictions.cost_per_hour,
                func.count().label('count')
            ).group_by(ParkingRestrictions.cost_per_hour).order_by(ParkingRestrictions.cost_per_hour).all()
            
            return jsonify({
                'status': 'success',
                'statistics': [
                    {
                        'cost_cents': cost,
                        'cost_dollars': round(cost / 100.0, 2),
                        'count': count
                    }
                    for cost, count in cost_distribution
                ]
            })
        
        else:
            return jsonify({
                'status': 'error',
                'message': 'Invalid statistics type. Use "overall", "daily", or "cost"'
            }), 400
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to fetch statistics: {str(e)}'
        }), 500

@restrictions_bp.route('/search', methods=['GET'])
def search_restrictions():
    """
    Search parking restrictions with various filters
    
    Query Parameters:
        zone_id (int): Filter by specific zone
        day_of_week (str): Filter by day of week (1-7)
        start_time (str): Filter by start time (HH:MM)
        end_time (str): Filter by end time (HH:MM)
        min_cost (int): Minimum cost per hour in cents
        max_cost (int): Maximum cost per hour in cents
        min_stay (int): Minimum stay in minutes
        max_stay (int): Maximum stay in minutes
        limit (int): Limit number of results (default: 100)
    """
    try:
        query = ParkingRestrictions.query
        
        # Apply filters
        zone_id = request.args.get('zone_id', type=int)
        if zone_id:
            query = query.filter(ParkingRestrictions.pay_stay_zone == zone_id)
        
        day_of_week = request.args.get('day_of_week')
        if day_of_week:
            if day_of_week not in ['1', '2', '3', '4', '5', '6', '7']:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid day_of_week. Must be 1-7 (Monday=1, Sunday=7)'
                }), 400
            query = query.filter(ParkingRestrictions.day_of_week == day_of_week)
        
        start_time_str = request.args.get('start_time')
        if start_time_str:
            try:
                start_time = datetime.strptime(start_time_str, '%H:%M').time()
                query = query.filter(ParkingRestrictions.start_time >= start_time)
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid start_time format. Use HH:MM'
                }), 400
        
        end_time_str = request.args.get('end_time')
        if end_time_str:
            try:
                end_time = datetime.strptime(end_time_str, '%H:%M').time()
                query = query.filter(ParkingRestrictions.end_time <= end_time)
            except ValueError:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid end_time format. Use HH:MM'
                }), 400
        
        min_cost = request.args.get('min_cost', type=int)
        if min_cost is not None:
            query = query.filter(ParkingRestrictions.cost_per_hour >= min_cost)
        
        max_cost = request.args.get('max_cost', type=int)
        if max_cost is not None:
            query = query.filter(ParkingRestrictions.cost_per_hour <= max_cost)
        
        min_stay = request.args.get('min_stay', type=int)
        if min_stay is not None:
            query = query.filter(ParkingRestrictions.minimum_stay >= min_stay)
        
        max_stay = request.args.get('max_stay', type=int)
        if max_stay is not None:
            query = query.filter(ParkingRestrictions.maximum_stay <= max_stay)
        
        # Order and limit results
        query = query.order_by(ParkingRestrictions.pay_stay_zone, ParkingRestrictions.day_of_week, ParkingRestrictions.start_time)
        
        limit = request.args.get('limit', default=100, type=int)
        restrictions = query.limit(limit).all()
        
        return jsonify({
            'status': 'success',
            'count': len(restrictions),
            'restrictions': [restriction.to_dict() for restriction in restrictions]
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to search restrictions: {str(e)}'
        }), 500
