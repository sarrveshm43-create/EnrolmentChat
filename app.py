import os
import datetime
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler

# Load environment variables from .env file
load_dotenv()

from flask import Flask
from flask_caching import Cache
from flask_login import LoginManager
from models.database import db

# Initialize extensions
cache = Cache()
login_manager = LoginManager()

def create_app(test_config=None):
    """Application factory function"""
    app = Flask(__name__, instance_relative_config=True)

    # Default configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev_key_change_in_production"),
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{os.path.join(app.instance_path, 'msu_chatbot.sqlite')}",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        CACHE_TYPE="SimpleCache",
        CACHE_DEFAULT_TIMEOUT=300,
        UPLOAD_FOLDER=os.path.join(app.static_folder, "uploads"),
        PDF_FOLDER=os.path.join(app.static_folder, "pdfs"),
        SESSION_TYPE="filesystem"
    )

    # Configure logging
    if not os.path.exists('logs'):
        os.makedirs('logs')
    file_handler = RotatingFileHandler('logs/msu_ai.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('MSU AI startup')

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Ensure the upload and PDF folders exist
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["PDF_FOLDER"], exist_ok=True)

    # Initialize extensions with app
    db.init_app(app)
    cache.init_app(app)
    
    # Configure Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'admin.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    # Set session protection to strong for better security
    login_manager.session_protection = 'strong'

    @login_manager.user_loader
    def load_user(user_id):
        from models.database import User
        try:
            user = User.query.get(int(user_id))
            if user and user.is_active:
                return user
            return None
        except Exception as e:
            app.logger.error(f"Error loading user: {str(e)}")
            return None

    # Add context processor for template variables
    @app.context_processor
    def inject_current_year():
        return {"current_year": datetime.datetime.now().year}

    # Create database tables
    with app.app_context():
        try:
            db.create_all()
            app.logger.info('Database tables created successfully')
        except Exception as e:
            app.logger.error(f'Error creating database tables: {str(e)}')

    # Register blueprints - import here to avoid circular imports
    from blueprints.main import main as main_blueprint
    from blueprints.admin import admin as admin_blueprint
    from blueprints.api import api as api_blueprint
    from blueprints.chat_controller import chat_bp

    app.register_blueprint(main_blueprint)
    app.register_blueprint(admin_blueprint, url_prefix="/admin")
    app.register_blueprint(api_blueprint, url_prefix="/api")
    app.register_blueprint(chat_bp)

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
