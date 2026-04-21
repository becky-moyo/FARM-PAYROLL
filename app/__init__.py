from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    from app.routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.routes.employees import bp as employees_bp
    app.register_blueprint(employees_bp, url_prefix='/employees')

    from app.routes.job_types import bp as job_types_bp
    app.register_blueprint(job_types_bp, url_prefix='/job-types')

    from app.routes.daily_logs import bp as daily_logs_bp
    app.register_blueprint(daily_logs_bp, url_prefix='/daily-logs')

    from app.routes.salary_slips import bp as salary_slips_bp
    app.register_blueprint(salary_slips_bp, url_prefix='/salary-slips')

    from app.routes.reports import bp as reports_bp
    app.register_blueprint(reports_bp, url_prefix='/reports')

    from app.routes.main import bp as main_bp
    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()
        from app.utils import seed_default_data, recalculate_all_daily_totals
        seed_default_data()
        recalculate_all_daily_totals()

    return app
