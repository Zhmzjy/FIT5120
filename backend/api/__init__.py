# Melbourne Parking API Module
"""
Melbourne Real-time Parking API

This module provides a clean, organized API structure for the Melbourne parking system.
It separates concerns into models, routes, services, and utilities for better maintainability.
"""

from flask import Blueprint

# Create API blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Import routes to register them with the blueprint
# Routes will be imported after db is initialized to avoid circular imports

# Export db from models - will be imported after initialization

__version__ = '1.0.0'
__author__ = 'FIT5120 Team'
