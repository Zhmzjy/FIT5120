#!/usr/bin/env python3
"""
Production entry point for Render.com deployment
"""
import os
from main import create_app, initialize_database

# Create the Flask application instance
app = create_app()

# Initialize database and fetch data when the app starts
if __name__ != "__main__":
    # This runs when imported by Gunicorn
    print("🚀 Initializing Melbourne Parking System for production...")
    try:
        initialize_database(app)
        print("✅ Production initialization completed!")
    except Exception as e:
        print(f"❌ Production initialization failed: {e}")

if __name__ == "__main__":
    # This will only run in development
    initialize_database(app)
    app.run(host='0.0.0.0', port=5000, debug=False)
