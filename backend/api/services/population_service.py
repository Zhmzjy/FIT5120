from datetime import datetime
from typing import Dict

class PopulationService:
    """Provides Melbourne CBD population growth trend data"""

    @classmethod
    def get_population_data(cls) -> Dict:
        try:
            
            years = list(range(2015, 2024))
            population_counts = [
                128000, 131500, 135000,
                140000, 144000, 142000,
                148000, 152000, 155500
            ]

            return {
                'success': True,
                'years': years,
                'counts': population_counts,
                'last_updated': datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'years': [],
                'counts': []
            }