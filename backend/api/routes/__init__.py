"""
Routes Module for Melbourne Parking API
"""

from flask import Blueprint
from .parking_routes import parking_bp
from .stats_routes import stats_bp
from .health_routes import health_bp
from .car_growth_routes import car_growth_bp
from .population_growth_routes import population_bp

def register_routes(app):
    """
    Register all API routes with the Flask app

    Args:
        app: Flask application instance
    """
    
    
    # Register health routes at root level - fix health check path
    app.register_blueprint(health_bp, url_prefix='')

    # Register parking routes
    app.register_blueprint(parking_bp, url_prefix='/api/parking')

    # Register stats routes
    app.register_blueprint(stats_bp, url_prefix='/api/stats')

    app.register_blueprint(car_growth_bp, url_prefix='/api/car-growth')

    app.register_blueprint(population_bp, url_prefix='/api/population')

__all__ = ['health_bp', 'parking_bp','stats_bp','car_growth_bp', 'population_bp']
