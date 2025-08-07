"""
On-Street Sensors Model for Melbourne Parking API
"""

from sqlalchemy import Column, Integer, String, DateTime, DECIMAL, Index, UniqueConstraint
from sqlalchemy.sql import func
from flask_sqlalchemy import SQLAlchemy

# Create a local db instance to avoid circular imports
db = SQLAlchemy()

class OnStreetSensors(db.Model):
    """On-Street Sensors model for real-time parking sensor data"""
    
    __tablename__ = 'on_street_sensors'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Core data fields
    kerbside_id = Column(Integer, nullable=False, unique=True, index=True)
    zone_number = Column(Integer, nullable=True, index=True)
    status_description = Column(String(50), nullable=False, index=True)
    last_updated = Column(DateTime(timezone=True), nullable=False, index=True)
    status_timestamp = Column(DateTime(timezone=True), nullable=False)
    latitude = Column(DECIMAL(10, 8), nullable=False)
    longitude = Column(DECIMAL(11, 8), nullable=False)
    
    # Foreign key to suburbs
    suburb_id = Column(Integer, db.ForeignKey('suburbs.id'), nullable=True)
    
    # Derived fields for quick queries
    suburb_name = Column(String(100), nullable=True, index=True)
    postcode = Column(String(10), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'kerbside_id': self.kerbside_id,
            'zone_number': self.zone_number,
            'status_description': self.status_description,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'status_timestamp': self.status_timestamp.isoformat() if self.status_timestamp else None,
            'latitude': float(self.latitude) if self.latitude else None,
            'longitude': float(self.longitude) if self.longitude else None,
            'suburb_name': self.suburb_name,
            'postcode': self.postcode,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_geojson(self):
        """Convert model to GeoJSON format"""
        return {
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [float(self.longitude), float(self.latitude)]
            },
            'properties': {
                'id': self.id,
                'kerbside_id': self.kerbside_id,
                'zone_number': self.zone_number,
                'status_description': self.status_description,
                'last_updated': self.last_updated.isoformat() if self.last_updated else None,
                'status_timestamp': self.status_timestamp.isoformat() if self.status_timestamp else None,
                'suburb_name': self.suburb_name,
                'postcode': self.postcode
            }
        }
    
    @classmethod
    def get_active_sensors(cls, hours=24):
        """Get sensors that have been updated within the specified hours"""
        from datetime import datetime, timedelta
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return cls.query.filter(cls.last_updated >= cutoff_time).all()
    
    @classmethod
    def get_sensors_by_status(cls, status):
        """Get sensors by status description"""
        return cls.query.filter(cls.status_description == status).all()
    
    @classmethod
    def get_sensors_by_suburb(cls, suburb_name):
        """Get sensors by suburb name"""
        return cls.query.filter(cls.suburb_name.ilike(f'%{suburb_name}%')).all()
    
    @classmethod
    def get_sensors_by_zone(cls, zone_number):
        """Get sensors by zone number"""
        return cls.query.filter(cls.zone_number == zone_number).all()
    
    @classmethod
    def get_sensors_near_location(cls, lat, lng, radius_km=2.0):
        """Get sensors within radius of specified location"""
        # Simple distance calculation (for small distances)
        # This is a rough approximation - for more accuracy, use PostGIS functions
        lat_diff = radius_km / 111.0  # Rough conversion to degrees
        lng_diff = radius_km / (111.0 * abs(lat) / 90.0)  # Adjust for latitude
        
        return cls.query.filter(
            cls.latitude.between(lat - lat_diff, lat + lat_diff),
            cls.longitude.between(lng - lng_diff, lng + lng_diff)
        ).all()
    
    @classmethod
    def get_statistics(cls):
        """Get overall sensor statistics"""
        from sqlalchemy import func
        
        total = cls.query.count()
        occupied = cls.query.filter(cls.status_description == 'Present').count()
        available = cls.query.filter(cls.status_description == 'Unoccupied').count()
        
        return {
            'total_sensors': total,
            'occupied_sensors': occupied,
            'available_sensors': available,
            'occupancy_rate': round((occupied / total * 100), 2) if total > 0 else 0
        }
    
    def __repr__(self):
        return f"<OnStreetSensors(kerbside_id={self.kerbside_id}, status={self.status_description}, lat={self.latitude}, lng={self.longitude})>"
