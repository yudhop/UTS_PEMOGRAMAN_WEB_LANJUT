"""Integritas data di level ORM/database: constraint, foreign key, cascade."""
import pytest
from sqlalchemy import func, inspect, select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Alert, Device, Sensor, TelemetryReading, User

from .factories import create_device, create_reading, create_rule, create_sensor, create_user

pytestmark = pytest.mark.usefixtures("app")  # semua test butuh app context + DB


def _count(model):
    return db.session.scalar(select(func.count()).select_from(model))


def test_schema_has_six_relevant_tables():
    tables = set(inspect(db.engine).get_table_names())
    assert {
        "users",
        "devices",
        "sensors",
        "telemetry_readings",
        "alert_rules",
        "alerts",
    } <= tables


def test_password_is_stored_as_hash():
    user = create_user(password="Password123")
    assert user.password_hash != "Password123"
    assert user.check_password("Password123")
    assert not user.check_password("salah")


def test_serial_number_must_be_unique():
    device = create_device()
    with pytest.raises(IntegrityError):
        create_device(owner=device.owner, serial_number=device.serial_number)
    db.session.rollback()


def test_foreign_key_is_enforced():
    with pytest.raises(IntegrityError):
        db.session.add(Sensor(device_id=9999, name="x", sensor_type="gas", unit="ppm"))
        db.session.commit()
    db.session.rollback()


def test_check_constraint_rejects_invalid_status():
    with pytest.raises(IntegrityError):
        create_device(status="exploded")
    db.session.rollback()


def test_owner_cannot_be_deleted_while_owning_devices():
    device = create_device()
    with pytest.raises(IntegrityError):
        db.session.delete(db.session.get(User, device.owner_id))
        db.session.commit()
    db.session.rollback()


def test_deleting_device_cascades_to_children_and_keeps_nothing_orphaned():
    sensor = create_sensor()
    rule = create_rule(sensor)
    reading = create_reading(sensor, value=50.0)
    db.session.add(Alert(rule_id=rule.id, reading_id=reading.id, severity="high", message="m"))
    db.session.commit()

    db.session.delete(db.session.get(Device, sensor.device_id))
    db.session.commit()

    for model in (Sensor, TelemetryReading, Alert):
        assert _count(model) == 0
