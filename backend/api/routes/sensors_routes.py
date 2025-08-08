"""
On-Street Sensors Routes for Melbourne Parking API
Handles real-time parking sensor data
"""

from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from sqlalchemy import func, distinct
from ..models import db, OnStreetSensors

# Create sensors routes blueprint
sensors_bp = Blueprint('sensors', __name__)

@sensors_bp.route('/sensors', methods=['GET'])
def get_sensors():
    """
    Get all parking sensors distributed across Melbourne zones

    Query Parameters:
        status (str): Filter by status (Present, Unoccupied, etc.)
        suburb (str): Filter by suburb name
        zone (int): Filter by zone number
        lat (float): Latitude for location-based filtering
        lng (float): Longitude for location-based filtering
        radius (float): Search radius in km (default: 2.0)
        active_hours (int): Only show sensors updated within X hours (default: 24)
        limit (int): Limit number of results (default: 100)
        distributed (bool): Whether to distribute results across zones (default: true)
    """
    try:
        limit = request.args.get('limit', default=100, type=int)
        distributed = request.args.get('distributed', default='true').lower() == 'true'

        base_query = OnStreetSensors.query

        # Apply filters
        status_filter = request.args.get('status')
        if status_filter:
            base_query = base_query.filter(OnStreetSensors.status_description == status_filter)

        suburb_filter = request.args.get('suburb')
        if suburb_filter:
            base_query = base_query.filter(OnStreetSensors.suburb_name.ilike(f'%{suburb_filter}%'))

        zone_filter = request.args.get('zone', type=int)
        if zone_filter:
            base_query = base_query.filter(OnStreetSensors.zone_number == zone_filter)

        # Filter by active hours - 放宽时间限制以获取更多数据
        active_hours = request.args.get('active_hours', default=168, type=int)  # 7天内的数据
        if active_hours > 0:
            cutoff_time = datetime.utcnow() - timedelta(hours=active_hours)
            base_query = base_query.filter(OnStreetSensors.last_updated >= cutoff_time)

        # Location-based filtering
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        radius = request.args.get('radius', default=2.0, type=float)
        
        if lat and lng:
            lat_diff = radius / 111.0
            lng_diff = radius / (111.0 * abs(lat) / 90.0) if lat != 0 else radius / 111.0

            base_query = base_query.filter(
                OnStreetSensors.latitude.between(lat - lat_diff, lat + lat_diff),
                OnStreetSensors.longitude.between(lng - lng_diff, lng + lng_diff)
            )
        
        if distributed and not zone_filter:
            # 获取不同区域均匀分布的数据
            sensors = get_distributed_sensors(base_query, limit)
        else:
            # 简单按时间排序获取数据
            sensors = base_query.order_by(OnStreetSensors.last_updated.desc()).limit(limit).all()

        # 转换为前端需要的格式
        result_data = []
        for sensor in sensors:
            sensor_dict = {
                'kerbsideid': sensor.kerbside_id,
                'zone_number': sensor.zone_number,
                'status_description': sensor.status_description,
                'lastupdated': sensor.last_updated.isoformat() if sensor.last_updated else None,
                'status_timestamp': sensor.status_timestamp.isoformat() if sensor.status_timestamp else None,
                'location': {
                    'lat': float(sensor.latitude) if sensor.latitude else None,
                    'lon': float(sensor.longitude) if sensor.longitude else None
                },
                'suburb_name': sensor.suburb_name,
                'data_source': 'on-street',
                'parking_type': 'On-Street',
                'parking_spaces': 1
            }
            result_data.append(sensor_dict)

        return jsonify(result_data)

    except Exception as e:
        print(f"Error in get_sensors: {str(e)}")
        return jsonify({
            'error': str(e),
            'status': 'error'
        }), 500

def get_distributed_sensors(base_query, limit=100):
    """
    获取在不同街道均匀分布的传感器数据
    通过地理位置分布确保数据来自不同街道
    """
    try:
        # 创建地理网格来分布数据点
        # Melbourne CBD 大致范围: lat -37.8-37.85, lng 144.95-145.0
        lat_min, lat_max = -37.85, -37.80
        lng_min, lng_max = 144.95, 145.00

        # 创建10x10的网格来分布数据
        grid_size = 10
        lat_step = (lat_max - lat_min) / grid_size
        lng_step = (lng_max - lng_min) / grid_size

        all_sensors = []
        sensors_per_grid = max(1, limit // (grid_size * grid_size))

        # 遍历网格，从每个网格区域获取数据
        for i in range(grid_size):
            for j in range(grid_size):
                if len(all_sensors) >= limit:
                    break

                # 计算当前网格的边界
                grid_lat_min = lat_min + i * lat_step
                grid_lat_max = lat_min + (i + 1) * lat_step
                grid_lng_min = lng_min + j * lng_step
                grid_lng_max = lng_min + (j + 1) * lng_step

                # 从当前网格获取传感器数据
                grid_sensors = base_query.filter(
                    OnStreetSensors.latitude.between(grid_lat_min, grid_lat_max),
                    OnStreetSensors.longitude.between(grid_lng_min, grid_lng_max)
                ).order_by(
                    OnStreetSensors.last_updated.desc()
                ).limit(sensors_per_grid).all()

                all_sensors.extend(grid_sensors)

        # 如果网格方法获取的数据不够，使用距离分布方法作为备选
        if len(all_sensors) < limit // 2:
            return get_distance_distributed_sensors(base_query, limit)

        # 按最后更新时间排序并限制结果
        all_sensors.sort(key=lambda x: x.last_updated if x.last_updated else datetime.min, reverse=True)
        return all_sensors[:limit]

    except Exception as e:
        print(f"Error in get_distributed_sensors: {str(e)}")
        # 如果出错，回退到简单查询
        return base_query.order_by(OnStreetSensors.last_updated.desc()).limit(limit).all()

def get_distance_distributed_sensors(base_query, limit=100):
    """
    使用最小距离分布算法获取来自不同位置的传感器
    确保选择的停车位之间有足够的距离间隔
    """
    try:
        # 获取所有可用的传感器
        all_available = base_query.order_by(OnStreetSensors.last_updated.desc()).limit(limit * 3).all()

        if not all_available:
            return []

        selected_sensors = []
        min_distance = 0.002  # 约200米的最小距离间隔

        for sensor in all_available:
            if len(selected_sensors) >= limit:
                break

            # 检查与已选择传感器的距离
            too_close = False
            for selected in selected_sensors:
                if sensor.latitude and sensor.longitude and selected.latitude and selected.longitude:
                    # 简单的欧几里得距离计算
                    lat_diff = abs(float(sensor.latitude) - float(selected.latitude))
                    lng_diff = abs(float(sensor.longitude) - float(selected.longitude))
                    distance = (lat_diff ** 2 + lng_diff ** 2) ** 0.5

                    if distance < min_distance:
                        too_close = True
                        break

            if not too_close:
                selected_sensors.append(sensor)

        return selected_sensors

    except Exception as e:
        print(f"Error in get_distance_distributed_sensors: {str(e)}")
        return base_query.order_by(OnStreetSensors.last_updated.desc()).limit(limit).all()

@sensors_bp.route('/sensors/zones', methods=['GET'])
def get_available_zones():
    """获取可用的区域列表"""
    try:
        zones = db.session.query(
            OnStreetSensors.zone_number,
            func.count(OnStreetSensors.id).label('sensor_count')
        ).filter(
            OnStreetSensors.zone_number.isnot(None)
        ).group_by(
            OnStreetSensors.zone_number
        ).order_by(
            OnStreetSensors.zone_number
        ).all()
        
        return jsonify([{
            'zone_number': zone.zone_number,
            'sensor_count': zone.sensor_count
        } for zone in zones])

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@sensors_bp.route('/sensors/stats', methods=['GET'])
def get_sensors_stats():
    """获取传感器统计信息"""
    try:
        total_sensors = OnStreetSensors.query.count()

        # 按状态分组统计
        status_stats = db.session.query(
            OnStreetSensors.status_description,
            func.count(OnStreetSensors.id).label('count')
        ).group_by(
            OnStreetSensors.status_description
        ).all()

        # 按区域统计
        zone_stats = db.session.query(
            OnStreetSensors.zone_number,
            func.count(OnStreetSensors.id).label('count')
        ).filter(
            OnStreetSensors.zone_number.isnot(None)
        ).group_by(
            OnStreetSensors.zone_number
        ).order_by(
            func.count(OnStreetSensors.id).desc()
        ).limit(10).all()

        return jsonify({
            'total_sensors': total_sensors,
            'status_distribution': [
                {'status': stat.status_description, 'count': stat.count}
                for stat in status_stats
            ],
            'top_zones': [
                {'zone': stat.zone_number, 'count': stat.count}
                for stat in zone_stats
            ]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
