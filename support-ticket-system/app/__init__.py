from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_marshmallow import Marshmallow
from flasgger import Swagger

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
ma = Marshmallow()


def create_app(config=None):
    app = Flask(__name__)

    if config is None:
        from config import Config
        app.config.from_object(Config)
    else:
        app.config.from_object(config)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    ma.init_app(app)

    _configure_swagger(app)

    from app.routes.auth import auth_bp
    from app.routes.tickets import tickets_bp
    from app.routes.users import users_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(tickets_bp, url_prefix="/api/tickets")
    app.register_blueprint(users_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")

    from app.utils.error_handlers import register_error_handlers
    register_error_handlers(app)

    # Boot the notification service so it has access to the app config
    from app.services.notification_service import notification_service
    notification_service.init_app(app)

    return app


def _configure_swagger(app):
    swagger_config = {
        "headers": [],
        "specs": [{"endpoint": "apispec", "route": "/apispec.json",
                   "rule_filter": lambda rule: True, "model_filter": lambda tag: True}],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/docs/",
    }
    template = {
        "info": {"title": "Support Ticket System API",
                 "description": "Customer Support Ticket Management System",
                 "version": "1.0.0"},
        "securityDefinitions": {
            "Bearer": {"type": "apiKey", "name": "Authorization",
                       "in": "header", "description": "JWT token: Bearer <token>"}
        },
    }
    Swagger(app, config=swagger_config, template=template)
