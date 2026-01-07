"""
Flask Application Factory
Initializes Flask app with extensions and blueprints.
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone, timedelta

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail

from app.backend.config import config

# IST Timezone (UTC+5:30)
IST = timezone(timedelta(hours=5, minutes=30))

# Initialize Flask extensions
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
mail = Mail()

# Configure Flask-Login
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'
login_manager.session_protection = 'strong'  # Enhanced session security


def create_app(config_name=None):
    """
    Application factory function.
    
    Args:
        config_name: Configuration to use (development, production, testing)
    
    Returns:
        Configured Flask application instance
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'development')
    
    # Get the path to frontend folder for templates and static files
    frontend_folder = os.path.join(os.path.dirname(__file__), 'frontend')
    template_folder = os.path.join(frontend_folder, 'templates')
    static_folder = os.path.join(frontend_folder, 'static')
    
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
    app.config.from_object(config[config_name])
    
    # Ensure instance folder exists for SQLite database
    instance_path = os.path.join(os.path.dirname(app.root_path), 'instance')
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)
    
    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    
    # Register blueprints
    from app.backend.routes.auth import auth_bp
    from app.backend.routes.dashboard import dashboard_bp
    from app.backend.routes.tasks import tasks_bp
    from app.backend.routes.projects import projects_bp
    from app.backend.routes.admin import admin_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(admin_bp)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Configure logging
    if not app.debug and not app.testing:
        configure_logging(app)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Register template filters for IST time
    @app.template_filter('ist_datetime')
    def ist_datetime_filter(dt, format='%d %b %Y, %I:%M %p IST'):
        """Convert datetime to IST and format it."""
        if dt is None:
            return ''
        if dt.tzinfo is None:
            # Assume the datetime is already in IST
            return dt.strftime(format)
        return dt.astimezone(IST).strftime(format)
    
    @app.template_filter('ist_date')
    def ist_date_filter(dt, format='%d %b %Y'):
        """Format date for display."""
        if dt is None:
            return ''
        if hasattr(dt, 'strftime'):
            return dt.strftime(format)
        return str(dt)
    
    @app.context_processor
    def inject_ist_now():
        """Inject current IST time into all templates."""
        return {'ist_now': datetime.now(IST)}
    
    return app


def register_error_handlers(app):
    """Register custom error handlers."""
    from flask import render_template
    
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500


def configure_logging(app):
    """Configure application logging."""
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    file_handler = RotatingFileHandler(
        'logs/taskmanager.log',
        maxBytes=10240000,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Task Manager startup')
