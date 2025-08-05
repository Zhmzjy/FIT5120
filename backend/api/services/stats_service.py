"""
Statistics Service for Melbourne Parking System
Handles parking statistics and analytics
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
from ..models import ParkingSensor, ParkingLot

class StatsService:
    """Service for generating parking statistics and analytics"""

    @classmethod
    def get_parking_overview(cls) -> Dict:
        """
        Get overall parking statistics

        Returns:
            Dictionary containing parking overview statistics
        """
        try:
            total_sensors = ParkingSensor.query.count()
            available_sensors = ParkingSensor.query.filter(
                ParkingSensor.status_description == 'Unoccupied'
            ).count()
            occupied_sensors = ParkingSensor.query.filter(
                ParkingSensor.status_description == 'Occupied'
            ).count()

            # Calculate occupancy rate
            occupancy_rate = 0
            if total_sensors > 0:
                occupancy_rate = round((occupied_sensors / total_sensors * 100), 2)

            return {
                'total_sensors': total_sensors,
                'available': available_sensors,
                'occupied': occupied_sensors,
                'occupancy_rate': occupancy_rate,
                'last_updated': datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"Error getting parking overview: {e}")
            return {
                'total_sensors': 0,
                'available': 0,
                'occupied': 0,
                'occupancy_rate': 0,
                'last_updated': datetime.utcnow().isoformat(),
                'error': str(e)
            }

    @classmethod
    def get_zone_statistics(cls) -> Dict:
        """
        Get parking statistics by zone

        Returns:
            Dictionary containing zone-wise statistics
        """
        try:
            zones = {}
            sensors = ParkingSensor.query.all()

            for sensor in sensors:
                zone = sensor.zone_number or 'Unknown'
                if zone not in zones:
                    zones[zone] = {
                        'total': 0,
                        'available': 0,
                        'occupied': 0
                    }

                zones[zone]['total'] += 1
                if sensor.status_description == 'Unoccupied':
                    zones[zone]['available'] += 1
                elif sensor.status_description == 'Occupied':
                    zones[zone]['occupied'] += 1

            # Calculate occupancy rates for each zone
            for zone_data in zones.values():
                if zone_data['total'] > 0:
                    zone_data['occupancy_rate'] = round(
                        (zone_data['occupied'] / zone_data['total'] * 100), 2
                    )
                else:
                    zone_data['occupancy_rate'] = 0

            return {
                'zones': zones,
                'total_zones': len(zones),
                'last_updated': datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"Error getting zone statistics: {e}")
            return {
                'zones': {},
                'total_zones': 0,
                'last_updated': datetime.utcnow().isoformat(),
                'error': str(e)
            }

    @classmethod
    def get_parking_lots_stats(cls) -> Dict:
        """
        Get parking lot statistics

        Returns:
            Dictionary containing parking lot statistics
        """
        try:
            lots = ParkingLot.query.all()

            total_capacity = sum(lot.total_spaces for lot in lots)
            total_available = sum(lot.available_spaces for lot in lots)
            total_occupied = total_capacity - total_available

            occupancy_rate = 0
            if total_capacity > 0:
                occupancy_rate = round((total_occupied / total_capacity * 100), 2)

            return {
                'total_lots': len(lots),
                'total_capacity': total_capacity,
                'total_available': total_available,
                'total_occupied': total_occupied,
                'occupancy_rate': occupancy_rate,
                'lots': [lot.to_dict() for lot in lots],
                'last_updated': datetime.utcnow().isoformat()
            }

        except Exception as e:
            print(f"Error getting parking lots stats: {e}")
            return {
                'total_lots': 0,
                'total_capacity': 0,
                'total_available': 0,
                'total_occupied': 0,
                'occupancy_rate': 0,
                'lots': [],
                'last_updated': datetime.utcnow().isoformat(),
                'error': str(e)
            }
