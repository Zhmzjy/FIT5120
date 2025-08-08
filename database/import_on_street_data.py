#!/usr/bin/env python3
"""
On-Street停车传感器数据导入脚本
"""

import json
import psycopg2
from psycopg2.extras import execute_batch
import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 数据库配置
DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'parking_system'),
    'user': os.getenv('DB_USER', 'zhujunyi'),
    'password': os.getenv('DB_PASSWORD', ''),
    'port': os.getenv('DB_PORT', '5432')
}

def get_db_connection():
    """获取数据库连接"""
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        return conn
    except Exception as e:
        print(f"数据库连接失败: {e}")
        return None

def import_on_street_sensors(json_file_path):
    """导入on-street停车传感器数据"""
    print(f"开始导入 {json_file_path}...")

    # 读取JSON数据
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"成功读取 {len(data)} 条记录")
    except Exception as e:
        print(f"读取JSON文件失败: {e}")
        return False

    # 连接数据库
    conn = get_db_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor()

        # 准备插入数据
        insert_query = """
        INSERT INTO on_street_sensors (
            device_id, bay_id, st_marker_id, status,
            latitude, longitude, location, last_updated
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (device_id) DO UPDATE SET
            status = EXCLUDED.status,
            last_updated = EXCLUDED.last_updated
        """

        # 准备批量插入的数据
        batch_data = []
        for record in data:
            # 提取坐标信息
            lat = None
            lng = None
            location = record.get('location')

            if location and isinstance(location, dict):
                lat = location.get('latitude') or location.get('lat')
                lng = location.get('longitude') or location.get('lng')

            batch_data.append((
                record.get('device_id'),
                record.get('bay_id'),
                record.get('st_marker_id'),
                record.get('status', 'Unknown'),
                lat,
                lng,
                json.dumps(location) if location else None,
                record.get('last_updated')
            ))

        # 批量插入数据
        print("正在插入数据到数据库...")
        execute_batch(cursor, insert_query, batch_data, page_size=1000)

        conn.commit()
        print(f"成功导入 {len(batch_data)} 条记录")

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"数据导入失败: {e}")
        conn.rollback()
        conn.close()
        return False

def main():
    """主函数"""
    print("=== On-Street停车传感器数据导入工具 ===\n")

    # 检查数据库连接
    conn = get_db_connection()
    if not conn:
        print("无法连接到数据库，请检查配置")
        sys.exit(1)

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'on_street_sensors'")
        if cursor.fetchone()[0] == 0:
            print("数据库表不存在，请先运行数据库schema创建脚本")
            sys.exit(1)
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"检查数据库表失败: {e}")
        sys.exit(1)

    # 获取项目根目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    # 导入on-street传感器数据
    on_street_file = os.path.join(project_root, 'on-street-parking-bay-sensors.json')
    if os.path.exists(on_street_file):
        if import_on_street_sensors(on_street_file):
            print("✅ On-street停车传感器数据导入成功\n")
        else:
            print("❌ On-street停车传感器数据导入失败\n")
    else:
        print(f"⚠️  文件不存在: {on_street_file}\n")

    print("数据导入完成！")

if __name__ == '__main__':
    main()
