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

@app.route('/api/parking/stats')
def get_parking_stats():
    """获取停车场统计信息"""
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # 获取基本统计信息
        cursor.execute("""
            SELECT 
                COUNT(*) as total_facilities,
                SUM(parking_spaces) as total_spaces,
                AVG(parking_spaces) as avg_spaces,
                MAX(parking_spaces) as max_spaces
            FROM off_street_car_parks
        """)
        stats = cursor.fetchone()

        cursor.close()
        conn.close()

        return jsonify(dict(stats))

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/parking/search')
def search_parking():
    """搜索停车场"""
    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500

    try:
        # 获取查询参数
        suburb = request.args.get('suburb', '')
        limit = int(request.args.get('limit', 50))

        cursor = conn.cursor(cursor_factory=RealDictCursor)

        if suburb:
            cursor.execute("""
                SELECT * FROM off_street_car_parks 
                WHERE clue_small_area ILIKE %s 
                ORDER BY parking_spaces DESC 
                LIMIT %s
            """, (f'%{suburb}%', limit))
        else:
            cursor.execute("""
                SELECT * FROM off_street_car_parks 
                ORDER BY parking_spaces DESC 
                LIMIT %s
            """, (limit,))

        results = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify([dict(row) for row in results])

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8888)
