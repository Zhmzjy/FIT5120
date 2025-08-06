#!/usr/bin/env python3
"""
Production entry point for Render.com deployment
"""
from main import create_app

# Create the Flask application instance
app = create_app()

if __name__ == "__main__":
    # This will only run in development
    app.run(host='0.0.0.0', port=5000, debug=False)
