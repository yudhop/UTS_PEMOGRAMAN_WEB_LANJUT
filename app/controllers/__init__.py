"""Registrasi semua blueprint (lapisan Controller)."""


def register_blueprints(app):
    from .health_controller import bp as health_bp
    from .user_controller import bp as user_bp
    from .device_controller import bp as device_bp
    from .sensor_controller import bp as sensor_bp
    from .alert_rule_controller import bp as alert_rule_bp
    from .telemetry_controller import bp as telemetry_bp
    from .alert_controller import bp as alert_bp

    for blueprint in (health_bp, user_bp, device_bp, sensor_bp, alert_rule_bp, telemetry_bp, alert_bp):
        app.register_blueprint(blueprint)
