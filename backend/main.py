from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os
import time
import sys

# Import API modules
from api.models import db, ParkingSensor
from api.routes import register_routes
from api.services import MelbourneParkingService

# Load environment variables
load_dotenv()

def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    CORS(app)

    # Database configuration with automatic detection
    database_url = os.getenv('DATABASE_URL')

    # For Render.com PostgreSQL (production)
    if database_url and database_url.startswith('postgresql'):
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    # For local MySQL (development)
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
            'DATABASE_URL',
            'mysql+pymysql://root:password@mysql/fit5120_db'
        )

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions
    db.init_app(app)

    # Register API routes
    register_routes(app)

    return app

def initialize_database(app):
    """Initialize database and fetch initial data"""
    try:
        with app.app_context():
            # Wait for database connection
            max_retries = 30
            for i in range(max_retries):
                try:
                    db.create_all()
                    print("✅ Database connection successful!")
                    break
                except Exception as e:
                    print(f"Database connection attempt {i+1}/{max_retries} failed: {e}")
                    if i == max_retries - 1:
                        raise
                    time.sleep(2)

            # Initial data fetch from Melbourne Government API
            print("🔄 Fetching initial parking data from Melbourne Government API...")
            success = MelbourneParkingService.update_database()

            if success:
                sensor_count = ParkingSensor.query.count()
                print(f"✅ Successfully loaded {sensor_count} parking sensors")
            else:
                print("⚠️  Failed to fetch API data, using database defaults")

    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        sys.exit(1)

if __name__ == '__main__':
    print("🚀 Starting Melbourne Parking API Server...")

    # Create Flask app
    app = create_app()

    # Initialize database in both development and production
    # Remove the RENDER check to ensure data is always loaded
    initialize_database(app)

    # Get port from environment for production deployment
    port = int(os.getenv('PORT', 5000))
    debug_mode = os.getenv('FLASK_ENV') != 'production'

    print("📍 API Endpoints Available:")
    print("   - Health Check: /health")
    print("   - Live Parking: /api/parking/live")
    print("   - Search: /api/parking/search")
    print("   - Statistics: /api/stats")
    print("   - Update Data: /api/parking/update")

    print("🌐 Starting Flask application...")
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
