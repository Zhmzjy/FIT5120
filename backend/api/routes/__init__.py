"""
Routes Module for Melbourne Parking API
"""

from flask import Blueprint
from .parking_routes import parking_bp
from .stats_routes import stats_bp
from .health_routes import health_bp

def register_routes(app):
    """
    Register all API routes with the Flask app

    Args:
        app: Flask application instance
    """
    # Register health routes at root level
    app.register_blueprint(health_bp, url_prefix='/health')

    # Register parking routes
    app.register_blueprint(parking_bp, url_prefix='/api/parking')

    # Register stats routes
    app.register_blueprint(stats_bp, url_prefix='/api/stats')

__all__ = ['parking_bp', 'stats_bp', 'health_bp', 'register_routes']
