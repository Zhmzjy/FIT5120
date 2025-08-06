"""
Melbourne Parking Data Service
Handles communication with Melbourne Government Open Data API
"""

import requests
from datetime import datetime
from typing import List, Dict, Optional
from ..models import ParkingSensor, db

class MelbourneParkingService:
    """Service for fetching real-time parking data from Melbourne Government API"""

    API_BASE_URL = "https://data.melbourne.vic.gov.au/api/explore/v2.1/catalog/datasets/on-street-parking-bay-sensors/records"

    @classmethod
    def fetch_live_parking_data(cls, limit: int = 100, status_filter: str = None) -> List[Dict]:
        """
        Fetch real-time parking data from Melbourne Open Data API

        Args:
            limit: Maximum number of records to fetch (max 100 per API limits)
            status_filter: Filter by status ('Unoccupied', 'Occupied', or None for all)

        Returns:
            List of parking sensor records
        """
        try:
            # Use the correct API format with proper limits
            # Melbourne API only allows max 100 records per request
            actual_limit = min(limit, 100)  # Ensure we don't exceed API limits

            params = {
                'select': 'status_description,zone_number,kerbsideid,location,status_timestamp',
                'limit': actual_limit,
                'offset': 0,
                'order_by': 'status_timestamp DESC'
            }

            # Add status filter if specified (use proper syntax)
            if status_filter:
                params['where'] = f"status_description = '{status_filter}'"

            print(f"🔄 Fetching parking data from Melbourne Government API...")
            print(f"📊 Parameters: {params}")

            response = requests.get(cls.API_BASE_URL, params=params, timeout=30)

            print(f"📡 API Response Status: {response.status_code}")
            print(f"🔗 Request URL: {response.url}")

            if response.status_code != 200:
                print(f"❌ API Error Response: {response.text[:500]}")
                return []

            response.raise_for_status()

            data = response.json()
            results = data.get('results', [])

            print(f"✅ Successfully fetched {len(results)} real parking records from Melbourne Government!")
            return results

        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching parking data: {e}")
            return []
        except Exception as e:
            print(f"❌ Unexpected error in parking data fetch: {e}")
            return []

    @classmethod
    def update_database(cls) -> bool:
        """
        Update local database with latest parking sensor data from API

        Returns:
            True if update successful, False otherwise
        """
        try:
            parking_data = cls.fetch_live_parking_data()

            if not parking_data:
                print("No parking data received from API")
                return False

            updated_count = 0

            for record in parking_data:
                try:
                    # Extract required fields
                    location = record.get('location', {})
                    if not location or 'lat' not in location or 'lon' not in location:
                        continue

                    kerbside_id = record.get('kerbsideid')
                    if not kerbside_id:
                        continue

                    # Convert kerbside_id to string to match database field type
                    kerbside_id = str(kerbside_id)

                    # Parse timestamp
                    timestamp_str = record.get('status_timestamp')
                    status_timestamp = None
                    if timestamp_str:
                        try:
                            status_timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        except:
                            status_timestamp = datetime.utcnow()

                    # Convert zone_number to string to match database field type
                    zone_num = record.get('zone_number')
                    zone_number_str = str(zone_num) if zone_num is not None else None

                    # Update or create parking sensor record
                    sensor = ParkingSensor.query.filter_by(kerbside_id=kerbside_id).first()

                    if sensor:
                        # Update existing record
                        sensor.status_description = record.get('status_description', 'Unknown')
                        sensor.zone_number = zone_number_str
                        sensor.latitude = float(location['lat'])
                        sensor.longitude = float(location['lon'])
                        sensor.status_timestamp = status_timestamp
                        sensor.last_updated = datetime.utcnow()
                    else:
                        # Create new record
                        sensor = ParkingSensor(
                            kerbside_id=kerbside_id,
                            zone_number=zone_number_str,
                            status_description=record.get('status_description', 'Unknown'),
                            latitude=float(location['lat']),
                            longitude=float(location['lon']),
                            status_timestamp=status_timestamp,
                            last_updated=datetime.utcnow()
                        )
                        db.session.add(sensor)

                    updated_count += 1

                except Exception as e:
                    print(f"Error processing parking record: {e}")
                    continue

            db.session.commit()
            print(f"Successfully updated {updated_count} parking sensors in database")
            return True

        except Exception as e:
            print(f"Error updating parking database: {e}")
            db.session.rollback()
            return False
