from flask import Flask, jsonify, request
from flask_cors import CORS
import psycopg2
import json
import os
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# 加载环境变量文件
load_dotenv()

app = Flask(__name__)
CORS(app)

# Database configuration
DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'parking_system'),
    'user': os.getenv('DB_USER', 'zhujunyi'),
    'password': os.getenv('DB_PASSWORD', ''),
    'port': os.getenv('DB_PORT', '5432')
}

# 添加调试信息
print("=== 数据库配置调试信息 ===")
for key, value in DATABASE_CONFIG.items():
    print(f"{key}: {value}")
print("=" * 30)

def get_db_connection():
    """建立数据库连接"""
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

@app.route('/')
def health_check():
    """健康检查路由"""
    return jsonify({
        "status": "healthy",
        "message": "Melbourne Parking System API is running"
    })

@app.route('/api/health')
def api_health_check():
    """API健康检查路由"""
    return jsonify({
        "status": "healthy",
        "message": "Melbourne Parking System API is running",
        "version": "1.0.0"
    })

@app.route('/api/test-db')
def test_database():
    """测试数据库连接"""
    conn = get_db_connection()
    if conn is None:
        return jsonify({
            "status": "error",
            "message": "Cannot connect to database"
        }), 500

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        cursor.close()
        conn.close()

        return jsonify({
            "status": "success",
            "message": "Database connection successful",
            "postgres_version": version[0]
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Database query failed: {str(e)}"
        }), 500

@app.route('/api/parking/search')
def search_parking():
    """搜索停车场"""
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # 获取查询参数
        suburb = request.args.get('suburb', '')
        parking_type = request.args.get('type', 'all')  # all, on-street, off-street
        limit = int(request.args.get('limit', 500))

        cursor = conn.cursor(cursor_factory=RealDictCursor)

        results = []

        # 根据停车类型筛选数据 - 修改逻辑确保 off-street 不包含 on-street 数据
        if parking_type == 'off-street':
            # 只查询off-street数据，不包含on-street
            off_street_query = """
                SELECT 
                    id, building_address, parking_type, parking_spaces,
                    latitude, longitude, clue_small_area, census_year,
                    'off-street' as data_source
                FROM off_street_car_parks 
                WHERE 1=1
            """
            params = []

            if suburb:
                off_street_query += " AND clue_small_area ILIKE %s"
                params.append(f'%{suburb}%')

            off_street_query += " ORDER BY parking_spaces DESC LIMIT %s"
            params.append(limit)

            cursor.execute(off_street_query, params)
            off_street_results = cursor.fetchall()
            results.extend([dict(row) for row in off_street_results])

        elif parking_type == 'on-street':
            # 只查询on-street数据，限制为100个
            on_street_query = """
                SELECT 
                    id, device_id as building_address, 'On-Street' as parking_type, 
                    1 as parking_spaces, latitude, longitude, 
                    bay_id as clue_small_area, status, last_updated,
                    'on-street' as data_source
                FROM on_street_sensors 
                WHERE latitude IS NOT NULL
            """
            on_street_params = []

            if suburb:
                on_street_query += " AND bay_id ILIKE %s"
                on_street_params.append(f'%{suburb}%')

            on_street_query += " ORDER BY id LIMIT 100"  # 限制为100个

            cursor.execute(on_street_query, on_street_params)
            on_street_results = cursor.fetchall()

            # 处理longitude为空的情况
            for row in on_street_results:
                row_dict = dict(row)
                if not row_dict.get('longitude'):
                    row_dict['longitude'] = 144.9631  # 使用墨尔本CBD默认经度
                results.append(row_dict)

        else:  # parking_type == 'all'
            # 显示所有类型，但on-street限制为100个
            # Off-street数据
            off_street_query = """
                SELECT 
                    id, building_address, parking_type, parking_spaces,
                    latitude, longitude, clue_small_area, census_year,
                    'off-street' as data_source
                FROM off_street_car_parks 
                WHERE 1=1
            """
            params = []

            if suburb:
                off_street_query += " AND clue_small_area ILIKE %s"
                params.append(f'%{suburb}%')

            off_street_query += " ORDER BY parking_spaces DESC LIMIT %s"
            params.append(limit // 2)  # 给off-street分配一半的限制

            cursor.execute(off_street_query, params)
            off_street_results = cursor.fetchall()
            results.extend([dict(row) for row in off_street_results])

            # On-street数据，限制为100个
            on_street_query = """
                SELECT 
                    id, device_id as building_address, 'On-Street' as parking_type, 
                    1 as parking_spaces, latitude, longitude, 
                    bay_id as clue_small_area, status, last_updated,
                    'on-street' as data_source
                FROM on_street_sensors 
                WHERE latitude IS NOT NULL
            """
            on_street_params = []

            if suburb:
                on_street_query += " AND bay_id ILIKE %s"
                on_street_params.append(f'%{suburb}%')

            on_street_query += " ORDER BY id LIMIT 100"  # 限制为100个

            cursor.execute(on_street_query, on_street_params)
            on_street_results = cursor.fetchall()

            # 处理longitude为空的情况
            for row in on_street_results:
                row_dict = dict(row)
                if not row_dict.get('longitude'):
                    row_dict['longitude'] = 144.9631  # 使用墨尔本CBD默认经度
                results.append(row_dict)

        cursor.close()
        conn.close()

        return jsonify(results[:limit])

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/parking/stats')
def get_parking_stats():
    """获取停车场统计信息"""
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # 获取off-street统计
        cursor.execute("""
            SELECT 
                COUNT(*) as off_street_facilities,
                SUM(parking_spaces) as off_street_spaces,
                AVG(parking_spaces) as avg_off_street_spaces,
                MAX(parking_spaces) as max_off_street_spaces
            FROM off_street_car_parks
        """)
        off_street_stats = cursor.fetchone()

        # 获取on-street统计
        cursor.execute("""
            SELECT 
                COUNT(*) as on_street_sensors,
                COUNT(CASE WHEN status = 'Present' THEN 1 END) as occupied_sensors,
                COUNT(CASE WHEN status = 'Unoccupied' THEN 1 END) as available_sensors
            FROM on_street_sensors
        """)
        on_street_stats = cursor.fetchone()

        cursor.close()
        conn.close()

        # 合并统计数据
        total_spaces = (off_street_stats['off_street_spaces'] or 0) + (on_street_stats['on_street_sensors'] or 0)
        total_facilities = (off_street_stats['off_street_facilities'] or 0) + (on_street_stats['on_street_sensors'] or 0)

        occupancy_rate = 0
        if on_street_stats['on_street_sensors'] > 0:
            occupancy_rate = round((on_street_stats['occupied_sensors'] / on_street_stats['on_street_sensors']) * 100, 1)

        return jsonify({
            "total_facilities": total_facilities,
            "total_spaces": total_spaces,
            "off_street_facilities": off_street_stats['off_street_facilities'],
            "off_street_spaces": off_street_stats['off_street_spaces'],
            "on_street_sensors": on_street_stats['on_street_sensors'],
            "occupied_sensors": on_street_stats['occupied_sensors'],
            "available_sensors": on_street_stats['available_sensors'],
            "occupancy_rate": occupancy_rate
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/sensors/sensors')
def get_sensors():
    """获取路边停车传感器数据"""
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # 获取查询参数
        status_filter = request.args.get('status', '')
        suburb = request.args.get('suburb', '')
        active_hours = int(request.args.get('active_hours', 24))
        limit = int(request.args.get('limit', 500))

        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # 构建查询SQL - 只要求latitude不为空（因为longitude数据缺失）
        query = """
            SELECT 
                id, device_id, bay_id, status, last_updated,
                latitude, longitude,
                'on-street' as data_source,
                'On-Street' as parking_type
            FROM on_street_sensors 
            WHERE latitude IS NOT NULL
        """
        params = []

        # 添加状态筛选
        if status_filter:
            query += " AND status = %s"
            params.append(status_filter)

        # 添加郊区筛选 - 只使用bay_id字段（如果不为空）
        if suburb:
            query += " AND bay_id ILIKE %s"
            params.append(f'%{suburb}%')

        # 暂时不添加时间筛选，因为last_updated字段也可能有问题
        # if active_hours > 0:
        #     query += " AND last_updated >= NOW() - INTERVAL '%s hours'"
        #     params.append(active_hours)

        query += " ORDER BY id LIMIT %s"
        params.append(limit)

        cursor.execute(query, params)
        results = cursor.fetchall()

        # 转换为字典列表
        sensors_data = []
        for row in results:
            sensor = dict(row)
            # 为缺失的字段提供默认值
            sensor['building_address'] = sensor.get('device_id') or f'Sensor-{sensor["id"]}'
            sensor['clue_small_area'] = sensor.get('bay_id') or 'Unknown Area'
            sensor['parking_spaces'] = 1  # 每个传感器代表1个停车位

            # 如果longitude为空，使用默认值（墨尔本CBD区域）
            if not sensor.get('longitude'):
                # 基于latitude估算longitude（墨尔本CBD大致在144.9-145.0之间）
                sensor['longitude'] = 144.9631  # 墨尔本CBD中心经度

            sensors_data.append(sensor)

        cursor.close()
        conn.close()

        return jsonify(sensors_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8889, debug=True)
