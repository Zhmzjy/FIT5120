"""
Parking Restrictions Model for Melbourne Parking API
"""

from sqlalchemy import Column, Integer, String, Time, DateTime, Index, UniqueConstraint
from sqlalchemy.sql import func
from .. import db

class ParkingRestrictions(db.Model):
    """Parking Restrictions model for pay-stay parking zones"""
    
    __tablename__ = 'parking_restrictions'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Core data fields
    pay_stay_zone = Column(Integer, nullable=False, index=True)
    day_of_week = Column(String(2), nullable=False, index=True)
    day_of_week_name = Column(String(20), nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    minimum_stay = Column(Integer, default=0)
    maximum_stay = Column(Integer, nullable=True)
    cost_per_hour = Column(Integer, nullable=False, index=True)
    
    # Metadata
    created_at = Column(DateTime, server_default=func.current_timestamp())
    updated_at = Column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Indexes and constraints
    __table_args__ = (
        Index('idx_restrictions_zone_day', 'pay_stay_zone', 'day_of_week'),
        Index('idx_restrictions_time_range', 'start_time', 'end_time'),
        UniqueConstraint('pay_stay_zone', 'day_of_week', 'start_time', 'end_time', 
                        name='uq_restrictions_zone_day_time'),
    )
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'pay_stay_zone': self.pay_stay_zone,
            'day_of_week': self.day_of_week,
            'day_of_week_name': self.day_of_week_name,
            'start_time': self.start_time.strftime('%H:%M') if self.start_time else None,
            'end_time': self.end_time.strftime('%H:%M') if self.end_time else None,
            'minimum_stay': self.minimum_stay,
            'maximum_stay': self.maximum_stay,
            'cost_per_hour': self.cost_per_hour,
            'cost_per_hour_dollars': round(self.cost_per_hour / 100.0, 2) if self.cost_per_hour else 0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_summary_dict(self):
        """Convert model to summary dictionary"""
        return {
            'pay_stay_zone': self.pay_stay_zone,
            'day_of_week': self.day_of_week,
            'day_of_week_name': self.day_of_week_name,
            'start_time': self.start_time.strftime('%H:%M') if self.start_time else None,
            'end_time': self.end_time.strftime('%H:%M') if self.end_time else None,
            'cost_per_hour_dollars': round(self.cost_per_hour / 100.0, 2) if self.cost_per_hour else 0,
            'maximum_stay_display': f"{self.maximum_stay} minutes" if self.maximum_stay else "No limit"
        }
    
    @classmethod
    def get_zone_restrictions(cls, zone_id):
        """Get all restrictions for a specific zone"""
        return cls.query.filter_by(pay_stay_zone=zone_id).order_by(cls.day_of_week, cls.start_time).all()
    
    @classmethod
    def get_day_restrictions(cls, day_of_week):
        """Get all restrictions for a specific day"""
        return cls.query.filter_by(day_of_week=day_of_week).order_by(cls.pay_stay_zone, cls.start_time).all()
    
    @classmethod
    def get_active_restrictions(cls, check_time, day_of_week):
        """Get restrictions active at a specific time and day"""
        return cls.query.filter(
            cls.day_of_week == day_of_week,
            cls.start_time <= check_time,
            cls.end_time >= check_time
        ).order_by(cls.cost_per_hour).all()
    
    @classmethod
    def get_zone_summary(cls, zone_id):
        """Get summary statistics for a zone"""
        restrictions = cls.query.filter_by(pay_stay_zone=zone_id).all()
        
        if not restrictions:
            return None
        
        return {
            'pay_stay_zone': zone_id,
            'total_restrictions': len(restrictions),
            'active_days': len(set(r.day_of_week for r in restrictions)),
            'min_cost_per_hour': min(r.cost_per_hour for r in restrictions),
            'max_cost_per_hour': max(r.cost_per_hour for r in restrictions),
            'avg_cost_per_hour': sum(r.cost_per_hour for r in restrictions) // len(restrictions),
            'min_stay_minutes': min(r.minimum_stay for r in restrictions),
            'max_stay_minutes': max(r.maximum_stay for r in restrictions if r.maximum_stay is not None)
        }
    
    @classmethod
    def get_cost_statistics(cls):
        """Get overall cost statistics"""
        from sqlalchemy import func
        
        result = db.session.query(
            func.min(cls.cost_per_hour).label('min_cost'),
            func.max(cls.cost_per_hour).label('max_cost'),
            func.avg(cls.cost_per_hour).label('avg_cost'),
            func.count().label('total_restrictions')
        ).first()
        
        return {
            'min_cost_cents': result.min_cost,
            'max_cost_cents': result.max_cost,
            'avg_cost_cents': round(result.avg_cost) if result.avg_cost else 0,
            'total_restrictions': result.total_restrictions
        }
    
    @classmethod
    def get_day_statistics(cls):
        """Get statistics by day of week"""
        from sqlalchemy import func
        
        results = db.session.query(
            cls.day_of_week,
            cls.day_of_week_name,
            func.count().label('total_restrictions'),
            func.count(func.distinct(cls.pay_stay_zone)).label('active_zones'),
            func.avg(cls.cost_per_hour).label('avg_cost'),
            func.min(cls.start_time).label('earliest_start'),
            func.max(cls.end_time).label('latest_end')
        ).group_by(cls.day_of_week, cls.day_of_week_name).order_by(cls.day_of_week).all()
        
        return [
            {
                'day_of_week': r.day_of_week,
                'day_of_week_name': r.day_of_week_name,
                'total_restrictions': r.total_restrictions,
                'active_zones': r.active_zones,
                'avg_cost_cents': round(r.avg_cost) if r.avg_cost else 0,
                'earliest_start': r.earliest_start.strftime('%H:%M') if r.earliest_start else None,
                'latest_end': r.latest_end.strftime('%H:%M') if r.latest_end else None
            }
            for r in results
        ]
    
    def __repr__(self):
        return f"<ParkingRestrictions(zone={self.pay_stay_zone}, day={self.day_of_week_name}, time={self.start_time}-{self.end_time}, cost=${self.cost_per_hour/100:.2f})>"
