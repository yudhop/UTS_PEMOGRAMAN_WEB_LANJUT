"""Pembuat data uji langsung lewat ORM (tanpa melalui API)."""
import itertools

from app.extensions import db
from app.models import AlertRule, Device, Sensor, TelemetryReading, User
from app.models.base import utcnow

_counter = itertools.count(1)


def _save(obj):
    db.session.add(obj)
    db.session.commit()
    return obj


def create_user(password="Password123", **overrides):
    n = next(_counter)
    data = {"username": f"user{n}", "email": f"user{n}@example.com", "role": "operator"}
    data.update(overrides)
    user = User(**data)
    user.set_password(password)
    return _save(user)


def create_device(owner=None, **overrides):
    n = next(_counter)
    owner = owner or create_user()
    data = {
        "owner_id": owner.id,
        "name": f"Device {n}",
        "serial_number": f"SN-{n:04d}",
        "device_type": "esp32",
        "status": "active",
    }
    data.update(overrides)
    return _save(Device(**data))


def create_sensor(device=None, **overrides):
    n = next(_counter)
    device = device or create_device()
    data = {
        "device_id": device.id,
        "name": f"Sensor {n}",
        "sensor_type": "temperature",
        "unit": "°C",
        "min_value": -40.0,
        "max_value": 125.0,
    }
    data.update(overrides)
    return _save(Sensor(**data))


def create_rule(sensor=None, **overrides):
    n = next(_counter)
    sensor = sensor or create_sensor()
    data = {
        "sensor_id": sensor.id,
        "name": f"Rule {n}",
        "operator": "gt",
        "threshold": 30.0,
        "severity": "high",
    }
    data.update(overrides)
    return _save(AlertRule(**data))


def create_reading(sensor=None, value=25.0, recorded_at=None):
    sensor = sensor or create_sensor()
    return _save(
        TelemetryReading(
            sensor_id=sensor.id, value=value, recorded_at=recorded_at or utcnow()
        )
    )
