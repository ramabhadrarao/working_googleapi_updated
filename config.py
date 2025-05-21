import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration class for the application."""
    # Application settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-should-be-changed-in-production')
    DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', 't', '1', 'yes', 'y')
    
    # Database configuration - SQLite by default
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///route_analytics.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # MongoDB configuration (optional)
    MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/route_analytics')
    
    # API keys
    GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')
    OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')
    
    # File upload settings
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload size
    
    # PDF reports settings
    REPORTS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'reports')
    
    # Session settings
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    
    # Create necessary directories
    @staticmethod
    def init_app(app):
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(app.config['REPORTS_FOLDER'], exist_ok=True)
        os.makedirs('compliance_data', exist_ok=True)
        os.makedirs('environmental_data', exist_ok=True)
        os.makedirs('logs', exist_ok=True)

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    
class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Production specific setup
        import logging
        from logging.handlers import RotatingFileHandler
        
        # Set up logging
        file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Route Analytics startup')

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}