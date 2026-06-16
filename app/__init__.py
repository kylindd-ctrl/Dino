import os
import logging
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()

def create_app(config_name=None):
    app = Flask(__name__)

    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")
    from app.config import config_map
    app.config.from_object(config_map.get(config_name, config_map["default"]))

    db.init_app(app)
    migrate.init_app(app, db)

    # Ensure storage directories exist
    for folder in [
        app.config["UPLOAD_FOLDER"],
        app.config["REFERENCE_FOLDER"],
        app.config["OUTPUT_FOLDER"],
    ]:
        os.makedirs(folder, exist_ok=True)

    # --- i18n context processor ---
    from app.translations import get_translations, get_language_label, get_alternate_lang

    @app.context_processor
    def inject_i18n():
        lang = request.cookies.get("lang", "zh")
        if lang not in ("zh", "en"):
            lang = "zh"
        t = get_translations(lang)
        t["_current_lang"] = lang
        t["_alternate_lang"] = get_alternate_lang(lang)
        t["_alternate_label"] = get_language_label(get_alternate_lang(lang))
        return {"_": t, "current_lang": lang}

    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.projects import projects_bp
    from app.routes.uploads import uploads_bp
    from app.routes.solar_data import solar_data_bp
    from app.routes.financial import financial_bp
    from app.routes.ppt import ppt_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(projects_bp, url_prefix="/api/projects")
    app.register_blueprint(uploads_bp)
    app.register_blueprint(solar_data_bp)
    app.register_blueprint(financial_bp)
    app.register_blueprint(ppt_bp)

    # Auto-create database tables if they do not exist
    with app.app_context():
        try:
            import sqlalchemy as sa
            from app.models import Project, PVSystem, PVModule, Inverter, SolarResource
            from app.models import MonthlyGeneration, HourlyGeneration, FinancialResult, Upload
            engine = sa.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
            db.Model.metadata.create_all(bind=engine)
            engine.dispose()
        except Exception as e:
            app.logger.warning("Table creation failed (non-fatal): %s", e)

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return {"error": "Not found"}, 404

    @app.errorhandler(500)
    def server_error(e):
        return {"error": "Internal server error"}, 500

    # Shell context for flask shell
    @app.shell_context_processor
    def make_shell_context():
        from app.models import Project, PVSystem, PVModule, Inverter
        from app.models import SolarResource, MonthlyGeneration, HourlyGeneration
        from app.models import FinancialResult, Upload
        return {
            "db": db,
            "Project": Project,
            "PVSystem": PVSystem,
            "PVModule": PVModule,
            "Inverter": Inverter,
            "SolarResource": SolarResource,
            "MonthlyGeneration": MonthlyGeneration,
            "HourlyGeneration": HourlyGeneration,
            "FinancialResult": FinancialResult,
            "Upload": Upload,
        }

    return app
