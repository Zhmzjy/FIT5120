from flask import Blueprint, jsonify

population_bp = Blueprint('population', __name__ )

@population_bp.route('/', methods=['GET'])
@population_bp.route('/trend', methods=['GET'])
def get_population_trend():
    """
    Get historical Melbourne CBD population growth trend
    """
    from ..services.population_service import PopulationService
    try:
        data = PopulationService.get_population_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500