from flask import Flask
from .config import Config
from .extensions import db, login_manager, bcrypt, migrate, session
from app.monitoring import APIMonitor, SystemMonitor
import colorlog
from app.colorlog import configure_logger
import os

def create_app(config_class=Config):
    configure_logger()
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)

    app.config['SESSION_TYPE'] = 'filesystem'
    session.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    # Initialize monitoring
    app.api_monitor = APIMonitor()
    app.system_monitor = SystemMonitor()

    # Initialize error handling and logging
    from app.errors import errors as errors_bp, init_logging
    app.register_blueprint(errors_bp)
    init_logging(app)

    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.teacher import teacher_bp
    from app.routes.student import student_bp
    from app.routes.monitoring import monitoring_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(monitoring_bp)

    # User loader callback
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        try:
            return db.session.get(User, int(user_id))
        except:
            return None

    # Create database tables
    with app.app_context():
        db.create_all()
        create_admin_user(app)

    # Ensure required directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.dirname(app.config['LOG_FILE']), exist_ok=True)
    
    # Add directory paths to logger
    app.logger.info(f"Upload directory: {app.config['UPLOAD_FOLDER']}")
    app.logger.info(f"Log directory: {os.path.dirname(app.config['LOG_FILE'])}")

    return app

def create_admin_user(app):
    with app.app_context():
        from app.models.user import User
        if not User.query.filter_by(role='admin').first():
            admin = User(
                username='admin',
                email='admin@example.com',
                role='admin',
                is_approved=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()