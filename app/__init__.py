"""Application factory untuk IoT Monitor API."""
from flask import Flask

from .config import get_config
from .extensions import db, migrate


def create_app(config_name=None):
    config_class = get_config(config_name)

    app = Flask(__name__)
    app.config.from_object(config_class)
    config_class.init_app(app)
    app.json.sort_keys = False  # urutan field JSON mengikuti schema

    db.init_app(app)
    migrate.init_app(app, db)

    from . import models  # noqa: F401  (daftarkan model untuk ORM & migration)
    from .controllers import register_blueprints
    from .utils.errors import register_error_handlers
    from .utils.security import register_security

    register_error_handlers(app)
    register_security(app)
    register_blueprints(app)

    from .cli import register_cli

    register_cli(app)
    return app
