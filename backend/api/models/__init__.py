"""
Database Models for Melbourne Parking System
Updated to match PostgreSQL schema
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

# Import models - temporarily commented to fix circular import
# from .parking_restrictions import ParkingRestrictions
from .on_street_sensors import OnStreetSensors

class Suburb(db.Model):
    """Suburb boundaries model"""
    __tablename__ = 'suburbs'

    id = db.Column(db.Integer, primary_key=True)
    lc_ply_pid = db.Column(db.Integer, unique=True)
    loc_pid = db.Column(db.String(20))
    suburb_name = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(10), default='VIC')
    postcode = db.Column(db.String(10))
    geometry_type = db.Column(db.String(20))
    coordinates = db.Column(db.JSON)  # JSONB in PostgreSQL
    created_date = db.Column(db.DateTime)
    retired_date = db.Column(db.DateTime)
    last_updated = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    parking_facilities = db.relationship('OffStreetParking', backref='suburb_ref', lazy=True)

    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'suburb_name': self.suburb_name,
            'postcode': self.postcode,
            'state': self.state,
            'coordinates': self.coordinates,
            'geometry_type': self.geometry_type,
            'parking_count': len(self.parking_facilities) if self.parking_facilities else 0
        }

class OffStreetParking(db.Model):
    """Commercial parking facilities model"""
    __tablename__ = 'off_street_parking'

    id = db.Column(db.Integer, primary_key=True)
    census_year = db.Column(db.String(4), nullable=False)
    block_id = db.Column(db.Integer)
    property_id = db.Column(db.String(20))
    base_property_id = db.Column(db.String(20))
    building_address = db.Column(db.Text, nullable=False)
    parking_type = db.Column(db.String(50), default='Commercial')
    parking_spaces = db.Column(db.Integer, nullable=False, default=0)
    latitude = db.Column(db.Numeric(10, 8), nullable=False)
    longitude = db.Column(db.Numeric(11, 8), nullable=False)

    # Foreign key to suburbs
    suburb_id = db.Column(db.Integer, db.ForeignKey('suburbs.id'))
    suburb_name = db.Column(db.String(100))  # Cached for quick queries
    postcode = db.Column(db.String(10))      # Cached for quick queries

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'building_address': self.building_address,
            'parking_spaces': self.parking_spaces,
            'parking_type': self.parking_type,
            'coordinates': [float(self.latitude), float(self.longitude)],
            'latitude': float(self.latitude),
            'longitude': float(self.longitude),
            'suburb_name': self.suburb_name,
            'postcode': self.postcode,
            'census_year': self.census_year
        }

    def to_geojson_feature(self):
        """Convert to GeoJSON feature format"""
        return {
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [float(self.longitude), float(self.latitude)]
            },
            'properties': {
                'id': self.id,
                'name': self.building_address,
                'parking_spaces': self.parking_spaces,
                'parking_type': self.parking_type,
                'suburb_name': self.suburb_name,
                'postcode': self.postcode
            }
        }

class ParkingSpaces(db.Model):
    """Individual parking spaces for real-time data"""
    __tablename__ = 'parking_spaces'

    id = db.Column(db.Integer, primary_key=True)
    off_street_parking_id = db.Column(db.Integer, db.ForeignKey('off_street_parking.id'))
    space_number = db.Column(db.Integer)
    status = db.Column(db.String(20), default='available')  # available, occupied, reserved, out_of_service
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('off_street_parking_id', 'space_number'),)

    def to_dict(self):
        return {
            'id': self.id,
            'space_number': self.space_number,
            'status': self.status,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }

# Legacy model for compatibility (if needed)
class ParkingSensor(db.Model):
    """Legacy real-time parking sensor data model"""
    __tablename__ = 'parking_sensors'

    id = db.Column(db.Integer, primary_key=True)
    kerbside_id = db.Column(db.Integer, unique=True, nullable=False)
    zone_number = db.Column(db.String(20), nullable=True)
    status_description = db.Column(db.String(50), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    status_timestamp = db.Column(db.DateTime, nullable=False)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'kerbside_id': self.kerbside_id,
            'zone_number': self.zone_number,
            'status': self.status_description,
            'coordinates': [self.latitude, self.longitude],
            'latitude': self.latitude,
            'longitude': self.longitude,
            'status_timestamp': self.status_timestamp.isoformat() if self.status_timestamp else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }
