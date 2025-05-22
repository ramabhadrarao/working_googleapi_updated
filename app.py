import os
from flask import Flask, render_template
from flask_login import current_user
from config import config
from models import db, login_manager
from flask_session import Session
import datetime

def create_app(config_name='default'):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    Session(app)
    
    # Setup error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500
    
    # Register blueprints
    from controllers.auth_controller import auth
    app.register_blueprint(auth, url_prefix='/auth')
    
    from controllers.route_controller import route_bp
    app.register_blueprint(route_bp, url_prefix='/routes')
    
    from controllers.summary_controller import summary_bp
    app.register_blueprint(summary_bp, url_prefix='/summary')
    
    from controllers.risk_controller import risk_bp
    app.register_blueprint(risk_bp, url_prefix='/risk')
    
    from controllers.compliance_controller import compliance_bp
    app.register_blueprint(compliance_bp, url_prefix='/compliance')
    
    from controllers.emergency_controller import emergency_bp
    app.register_blueprint(emergency_bp, url_prefix='/emergency')
    
    from controllers.environmental_controller import environmental_bp
    app.register_blueprint(environmental_bp, url_prefix='/environmental')
    
    from controllers.report_controller import report_bp
    app.register_blueprint(report_bp, url_prefix='/reports')
    
    # Main blueprint for index and other general pages
    from controllers.main_controller import main_bp
    app.register_blueprint(main_bp)
    # Add this import at the top with other blueprint imports
    from controllers.csv_upload_controller import csv_upload_bp
    app.register_blueprint(csv_upload_bp, url_prefix='/csv-upload')

    
    # Create all tables
    with app.app_context():
        db.create_all()
    @app.context_processor
    def inject_now():
        """Add current datetime to all templates."""
        return {'now': datetime.datetime.now()}
    
    # Inject variables into Jinja templates
    @app.context_processor
    def inject_user():
        return dict(user=current_user)
    
    return app

# Create the application instance using environment variable or default to development
app = create_app(os.getenv('FLASK_ENV', 'development'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)