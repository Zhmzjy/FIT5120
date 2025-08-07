#!/usr/bin/env python3
"""
Import on-street parking sensors data into PostgreSQL database
"""

import json
import psycopg2
from datetime import datetime
import sys
import os

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': '5432',
    'database': 'melbourne_parking',
    'user': 'melbourne_user',
    'password': 'melbourne_password'
}

def connect_db():
    """Connect to PostgreSQL database"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)

def parse_timestamp(timestamp_str):
    """Parse timestamp string to datetime object"""
    try:
        # Handle different timestamp formats
        if timestamp_str:
            # Try ISO format first
            try:
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except:
                # Try other common formats
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f']:
                    try:
                        return datetime.strptime(timestamp_str, fmt)
                    except:
                        continue
        return datetime.utcnow()
    except:
        return datetime.utcnow()

def import_sensors_data():
    """Import on-street sensors data from JSON file"""
    json_file = '../on-street-parking-bay-sensors.json'
    
    if not os.path.exists(json_file):
        print(f"❌ JSON file not found: {json_file}")
        return
    
    print(f"📁 Reading data from: {json_file}")
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Failed to read JSON file: {e}")
        return
    
    print(f"📊 Found {len(data)} sensor records")
    
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        # Clear existing data
        cursor.execute("DELETE FROM on_street_sensors")
        print("🗑️  Cleared existing sensor data")
        
        # Insert new data
        inserted_count = 0
        for record in data:
            try:
                # Parse timestamp
                last_updated = parse_timestamp(record.get('last_updated'))
                status_timestamp = parse_timestamp(record.get('status_timestamp'))
                
                # Extract location data
                location = record.get('location', {})
                latitude = location.get('lat')
                longitude = location.get('lon')
                
                # Insert sensor data
                cursor.execute("""
                    INSERT INTO on_street_sensors (
                        kerbside_id, zone_number, status_description, 
                        last_updated, status_timestamp, latitude, longitude,
                        suburb_id, suburb_name, postcode, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    record.get('kerbsideid'),
                    record.get('zone_number'),
                    record.get('status_description'),
                    last_updated,
                    status_timestamp,
                    latitude,
                    longitude,
                    None,  # suburb_id will be updated later
                    None,  # suburb_name will be updated later
                    None,  # postcode will be updated later
                    datetime.utcnow(),
                    datetime.utcnow()
                ))
                inserted_count += 1
                
            except Exception as e:
                print(f"⚠️  Failed to insert record {record.get('kerbside_id')}: {e}")
                continue
        
        # Update suburb information using spatial matching
        print("🗺️  Updating suburb information...")
        cursor.execute("""
            UPDATE on_street_sensors 
            SET suburb_id = s.id, suburb_name = s.suburb_name, postcode = s.postcode
            FROM suburbs s
            WHERE ST_Contains(
                ST_GeomFromGeoJSON(s.coordinates::text), 
                ST_SetSRID(ST_MakePoint(on_street_sensors.longitude, on_street_sensors.latitude), 4326)
            )
        """)
        
        conn.commit()
        print(f"✅ Successfully imported {inserted_count} sensor records")
        
        # Show statistics
        cursor.execute("SELECT COUNT(*) FROM on_street_sensors")
        total_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM on_street_sensors WHERE status_description = 'Unoccupied'")
        available_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM on_street_sensors WHERE status_description = 'Present'")
        occupied_count = cursor.fetchone()[0]
        
        print(f"📊 Sensor Statistics:")
        print(f"   Total sensors: {total_count}")
        print(f"   Available: {available_count}")
        print(f"   Occupied: {occupied_count}")
        print(f"   Availability rate: {round(available_count/total_count*100, 1)}%" if total_count > 0 else "   Availability rate: 0%")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Import failed: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    print("🚀 Starting on-street sensors data import...")
    import_sensors_data()
    print("✅ Import completed!")
