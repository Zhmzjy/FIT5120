
from datetime import datetime
from typing import Dict

class CarGrowthService:
    """Provides car ownership growth trend data"""

    @classmethod
    def get_growth_data(cls) -> Dict:
        try:
            years = list(range(2015, 2024))
            car_counts = [
                1100000, 1150000, 1190000,
                1250000, 1300000, 1280000,
                1350000, 1400000, 1450000
            ]

            return {
                'success': True,
                'years': years,
                'counts': car_counts,
                'last_updated': datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'years': [],
                'counts': []
            }