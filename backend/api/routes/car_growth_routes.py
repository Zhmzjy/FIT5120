from flask import Blueprint, jsonify
from ..services.car_growth_service import CarGrowthService

car_growth_bp = Blueprint('car_growth', __name__, url_prefix='/api/car-growth')

@car_growth_bp.route('/', methods=['GET'])
@car_growth_bp.route('/trend', methods=['GET'])
def get_car_growth_trend():
    """
    Get historical car ownership trend for Melbourne
    """
    try:
        data = CarGrowthService.get_growth_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500