"""
Routes Module for Melbourne Parking API
"""

from flask import Blueprint
# Import blueprints inside register_routes to avoid circular imports

def register_routes(app):
    """
    Register all API routes with the Flask app

    Args:
        app: Flask application instance
    """
    # Import blueprints here to avoid circular imports
    from .health_routes import health_bp
    from .parking_routes import parking_bp
    from .stats_routes import stats_bp
    # from .restrictions_routes import restrictions_bp
    # from .sensors_routes import sensors_bp
    
    # Register health routes at root level - fix health check path
    app.register_blueprint(health_bp, url_prefix='')

    # Register parking routes
    app.register_blueprint(parking_bp, url_prefix='/api/parking')

    # Register stats routes
    app.register_blueprint(stats_bp, url_prefix='/api/stats')

    # Register restrictions routes
    # app.register_blueprint(restrictions_bp, url_prefix='/api/restrictions')

    # Register sensors routes
    # app.register_blueprint(sensors_bp, url_prefix='/api/sensors')

__all__ = ['parking_bp', 'stats_bp', 'health_bp', 'restrictions_bp', 'sensors_bp', 'register_routes']
