"""
Database Models for Melbourne Parking System
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class ParkingSensor(db.Model):
    """Real-time parking sensor data model"""
    __tablename__ = 'parking_sensors'

    id = db.Column(db.Integer, primary_key=True)
    kerbside_id = db.Column(db.Integer, unique=True, nullable=False)  # Changed from String to Integer
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
            'latitude': self.latitude,  # Add explicit lat/lng for compatibility
            'longitude': self.longitude,
            'status_timestamp': self.status_timestamp.isoformat() if self.status_timestamp else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }

    def __repr__(self):
        return f'<ParkingSensor {self.kerbside_id}: {self.status_description}>'


class ParkingLot(db.Model):
    """Parking lot data model"""
    __tablename__ = 'parking_lots'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.String(300), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    total_spaces = db.Column(db.Integer, nullable=False)
    available_spaces = db.Column(db.Integer, nullable=False)
    price_per_hour = db.Column(db.Float, nullable=False)
    opening_hours = db.Column(db.String(100), nullable=False)
    area_type = db.Column(db.String(50), nullable=False)
    facilities = db.Column(db.Text)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'name': self.name,
            'address': self.address,
            'coordinates': [self.latitude, self.longitude],
            'total_spaces': self.total_spaces,
            'available_spaces': self.available_spaces,
            'price_per_hour': self.price_per_hour,
            'opening_hours': self.opening_hours,
            'area_type': self.area_type,
            'facilities': self.facilities.split(',') if self.facilities else [],
            'occupancy_rate': round(((self.total_spaces - self.available_spaces) / self.total_spaces * 100), 2) if self.total_spaces > 0 else 0,
            'last_updated': self.last_updated.isoformat()
        }

    def __repr__(self):
        return f'<ParkingLot {self.name}: {self.available_spaces}/{self.total_spaces}>'


class UserPreference(db.Model):
    """User preference data model"""
    __tablename__ = 'user_preferences'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), unique=True)
    preferred_radius = db.Column(db.Float, default=2.0)
    preferred_area = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'preferred_radius': self.preferred_radius,
            'preferred_area': self.preferred_area,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    def __repr__(self):
        return f'<UserPreference {self.session_id}: {self.preferred_area}>'
