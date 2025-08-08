from datetime import datetime
from typing import List, Dict
from ..models import CarGrowth, db

class CarGrowthService:
    """Service for retrieving and managing car ownership growth data"""

    @classmethod
    def get_growth_data(cls) -> Dict:
        """
        Fetch car growth data from the database
        Returns:
            Dictionary with years, counts, and metadata
        """
        try:
            records = CarGrowth.query.order_by(CarGrowth.year).all()
            return {
                'success': True,
                'years': [r.year for r in records],
                'counts': [r.count for r in records],
                'last_updated': datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'years': [],
                'counts': []
            }


    @classmethod
    def add_or_update(cls, year: int, count: int) -> bool:
        """
        Insert or update a car growth record
        """
        try:
            record = CarGrowth.query.filter_by(year=year).first()
            if record:
                record.count = count
            else:
                db.session.add(CarGrowth(year=year, count=count))
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error updating CarGrowth: {e}")
            return False