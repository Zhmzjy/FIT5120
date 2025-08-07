from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os
import time
import sys

# Import API modules - import db first to avoid circular imports
from api.models import db
from api.routes import register_routes

# Load environment variables
load_dotenv()

def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    CORS(app)

    # PostgreSQL database configuration
    database_url = os.getenv('DATABASE_URL')

    if database_url:
        # Use provided DATABASE_URL (for production/Render)
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        print(f"🔗 Using provided DATABASE_URL: {database_url.split('@')[0]}@***")
    else:
        # Local PostgreSQL configuration
        db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'melbourne_parking'),
            'user': os.getenv('DB_USER', 'melbourne_user'),
            'password': os.getenv('DB_PASSWORD', 'melbourne_password')
        }

        database_url = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        print(f"🔗 Using local PostgreSQL: {db_config['user']}@{db_config['host']}:{db_config['port']}/{db_config['database']}")

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_recycle': 300,
        'pool_pre_ping': True
    }

    # Initialize extensions
    db.init_app(app)

    # Register API routes
    register_routes(app)

    return app

def initialize_database():
    """Initialize database tables if they don't exist"""
    try:
        # Test database connection
        with db.engine.connect() as conn:
            print("✅ Database connection successful")

        # Note: Tables already exist from our import script
        # This is just for compatibility
        print("📊 Database tables are ready")

    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    app = create_app()

    with app.app_context():
        initialize_database()

    port = int(os.getenv('PORT', 5001))
    debug = os.getenv('FLASK_ENV') == 'development'

    print(f"🚀 Starting Melbourne Parking API on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
