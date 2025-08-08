from datetime import datetime
from typing import Dict
from ..models import PopulationGrowth, db  
class PopulationService:
    """Service for retrieving and managing Melbourne CBD population growth data"""

    @classmethod
    def get_population_data(cls) -> Dict:
        
        try:
            records = PopulationGrowth.query.order_by(PopulationGrowth.year).all()
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
        插入或更新人口增长记录
        """
        try:
            record = PopulationGrowth.query.filter_by(year=year).first()
            if record:
                record.count = count
            else:
                db.session.add(PopulationGrowth(year=year, count=count))
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error updating PopulationGrowth: {e}")
            return False