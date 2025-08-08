from flask import Blueprint, jsonify


car_growth_bp = Blueprint('car_growth', __name__)

@car_growth_bp.route('/', methods=['GET'])
@car_growth_bp.route('/trend', methods=['GET'])
def get_car_growth_trend():
    """
    Get historical car ownership trend for Melbourne
    """
    from ..services.car_growth_service import CarGrowthService
    try:
        data = CarGrowthService.get_growth_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500