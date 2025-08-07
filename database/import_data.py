#!/usr/bin/env python3
"""
数据导入脚本 - 将JSON数据导入PostgreSQL数据库
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

def import_off_street_parking(json_file_path):
    """导入off-street停车数据"""
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
        INSERT INTO off_street_car_parks (
            census_year, block_id, property_id, base_property_id,
            building_address, clue_small_area, parking_type,
            parking_spaces, longitude, latitude, location
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        # 准备批量插入的数据
        batch_data = []
        for record in data:
            batch_data.append((
                record.get('census_year'),
                record.get('block_id'),
                record.get('property_id'),
                record.get('base_property_id'),
                record.get('building_address'),
                record.get('clue_small_area'),
                record.get('parking_type'),
                record.get('parking_spaces'),
                record.get('longitude'),
                record.get('latitude'),
                json.dumps(record.get('location')) if record.get('location') else None
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

def import_suburb_boundaries(json_file_path):
    """导入suburb边界数据"""
    print(f"开始导入 {json_file_path}...")

    # 读取JSON数据
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 检查是否是FeatureCollection格式
        if isinstance(data, dict) and 'features' in data:
            features = data['features']
        elif isinstance(data, list):
            features = data
        else:
            print("不支持的JSON格式")
            return False

        print(f"成功读取 {len(features)} 条记录")
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
        INSERT INTO vic_suburb_boundaries (
            suburb_name, postcode, state, geometry
        ) VALUES (%s, %s, %s, %s)
        """

        # 准备批量插入的数据
        batch_data = []
        for feature in features:
            properties = feature.get('properties', {})
            geometry = feature.get('geometry', {})

            batch_data.append((
                properties.get('SUBURB_NAME') or properties.get('name'),
                properties.get('POSTCODE') or properties.get('postcode'),
                'VIC',
                json.dumps(geometry) if geometry else None
            ))

        # 批量插入数据
        print("正在插入数据到数据库...")
        execute_batch(cursor, insert_query, batch_data, page_size=100)

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
    print("=== Melbourne Parking System 数据导入工具 ===\n")

    # 检查数据库连接
    conn = get_db_connection()
    if not conn:
        print("无法连接到数据库，请检查配置")
        sys.exit(1)

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'off_street_car_parks'")
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

    # 导入off-street停车数据
    off_street_file = os.path.join(project_root, 'off-street-car-parks.json')
    if os.path.exists(off_street_file):
        if import_off_street_parking(off_street_file):
            print("✅ Off-street停车数据导入成功\n")
        else:
            print("❌ Off-street停车数据导入失败\n")
    else:
        print(f"⚠️  文件不存在: {off_street_file}\n")

    # 导入suburb边界数据
    suburb_file = os.path.join(project_root, 'vic_suburb_boundaries.json')
    if os.path.exists(suburb_file):
        if import_suburb_boundaries(suburb_file):
            print("✅ Suburb边界数据导入成功\n")
        else:
            print("❌ Suburb边界数据导入失败\n")
    else:
        print(f"⚠️  文件不存在: {suburb_file}\n")

    print("数据导入完成！")

if __name__ == '__main__':
    main()
