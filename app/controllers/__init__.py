"""Registrasi semua blueprint (lapisan Controller)."""


def register_blueprints(app):
    from .health_controller import bp as health_bp

    for blueprint in (health_bp,):
        app.register_blueprint(blueprint)
