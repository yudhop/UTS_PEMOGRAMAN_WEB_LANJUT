"""Logika penerimaan telemetri dari perangkat."""
from ..extensions import db
from ..models import TelemetryReading
from ..models.base import utcnow
from ..utils.errors import ApiError
from . import alert_service


def ingest_reading(sensor, value, recorded_at=None):
    """Simpan satu pembacaan, perbarui last_seen perangkat, lalu evaluasi alert.

    Mengembalikan (reading, daftar_alert_baru). Semua perubahan disimpan dalam
    satu transaksi.
    """
    device = sensor.device
    if device.status != "active":
        raise ApiError(
            409,
            "DEVICE_NOT_ACTIVE",
            f"Device '{device.name}' is {device.status}; "
            "telemetry is only accepted from active devices.",
        )

    low, high = sensor.min_value, sensor.max_value
    if (low is not None and value < low) or (high is not None and value > high):
        raise ApiError(
            422,
            "VALUE_OUT_OF_RANGE",
            "Reading is outside the physical range of this sensor.",
            {"value": [f"Must be between {low} and {high} {sensor.unit} for this sensor."]},
        )

    recorded_at = recorded_at or utcnow()
    reading = TelemetryReading(sensor_id=sensor.id, value=value, recorded_at=recorded_at)
    db.session.add(reading)
    if device.last_seen_at is None or recorded_at > device.last_seen_at:
        device.last_seen_at = recorded_at
    db.session.flush()

    alerts = alert_service.evaluate_reading(reading)
    db.session.commit()
    return reading, alerts
