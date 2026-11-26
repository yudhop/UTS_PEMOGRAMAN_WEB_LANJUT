"""Data simulasi (seed) untuk IoT Monitor API.

Seluruh data bersifat fiktif dan deterministik (random seed tetap).
Password semua user seed: "Password123" -> hanya untuk pengembangan lokal.
"""
import random
from datetime import timedelta

from sqlalchemy import delete, select

from app.extensions import db
from app.models import Alert, AlertRule, Device, Sensor, TelemetryReading, User
from app.models.base import utcnow
from app.services.alert_service import evaluate_reading, update_status

SEED_PASSWORD = "Password123"
READINGS_PER_SENSOR = 48  # 24 jam terakhir, tiap 30 menit
INTERVAL = timedelta(minutes=30)

USERS = [
    ("admin", "admin@example.com", "admin"),
    ("budi", "budi@example.com", "operator"),
    ("siti", "siti@example.com", "operator"),
    ("viewer", "viewer@example.com", "viewer"),
]

# (serial, name, type, location, status, firmware, owner_username)
DEVICES = [
    ("ESP32-GA-001", "Node Gudang A", "esp32", "Gudang A", "active", "1.2.0", "budi"),
    ("ESP32-GB-001", "Node Gudang B", "esp32", "Gudang B", "active", "1.2.0", "budi"),
    ("RPI-SRV-001", "Gateway Ruang Server", "raspberry_pi", "Ruang Server", "active", "2.0.1", "siti"),
    ("ESP8266-LAB-001", "Node Lab", "esp8266", "Laboratorium", "maintenance", "0.9.5", "siti"),
    ("ESP32-KA-001", "Node Kandang", "esp32", "Kandang Ayam", "inactive", "1.1.0", "budi"),
]

# (device_serial, name, type, unit, min, max, baseline, noise)
SENSORS = [
    ("ESP32-GA-001", "Suhu Gudang A", "temperature", "°C", -40, 125, 27.0, 1.2),
    ("ESP32-GA-001", "Kelembapan Gudang A", "humidity", "%", 0, 100, 62.0, 4.0),
    ("ESP32-GB-001", "Suhu Gudang B", "temperature", "°C", -40, 125, 26.0, 1.0),
    ("ESP32-GB-001", "Gas Gudang B", "gas", "ppm", 0, 10000, 350.0, 60.0),
    ("RPI-SRV-001", "Suhu Ruang Server", "temperature", "°C", -40, 125, 24.0, 0.8),
    ("RPI-SRV-001", "Tegangan UPS", "voltage", "V", 0, 300, 220.0, 2.0),
    ("ESP8266-LAB-001", "Cahaya Lab", "light", "lux", 0, 100000, 450.0, 60.0),
]

# (sensor_name, rule_name, operator, threshold, severity)
RULES = [
    ("Suhu Gudang A", "Gudang terlalu panas", "gt", 35.0, "high"),
    ("Kelembapan Gudang A", "Kelembapan tinggi", "gt", 80.0, "medium"),
    ("Gas Gudang B", "Kadar gas berbahaya", "gt", 1000.0, "critical"),
    ("Suhu Ruang Server", "Server overheating", "gt", 32.0, "critical"),
    ("Tegangan UPS", "Tegangan UPS turun", "lt", 200.0, "high"),
]

# Lonjakan buatan: nama sensor -> {posisi dari pembacaan terakhir: nilai}
SPIKES = {
    "Suhu Ruang Server": {2: 36.5, 1: 38.2, 0: 39.0},
    "Tegangan UPS": {20: 188.0},
    "Kelembapan Gudang A": {10: 84.5},
    "Gas Gudang B": {5: 1250.0},
}

RESET_ORDER = (Alert, AlertRule, TelemetryReading, Sensor, Device, User)


def reset_data():
    for model in RESET_ORDER:
        db.session.execute(delete(model))
    db.session.commit()


def run_seed(reset=False):
    """Isi database. Mengembalikan ringkasan jumlah data, atau None bila DB sudah terisi."""
    if reset:
        reset_data()
    elif db.session.scalar(select(User.id).limit(1)) is not None:
        return None

    rng = random.Random(42)
    now = utcnow().replace(microsecond=0)

    users = {}
    for username, email, role in USERS:
        user = User(username=username, email=email, role=role)
        user.set_password(SEED_PASSWORD)
        users[username] = user
    db.session.add_all(users.values())
    db.session.flush()

    devices = {}
    for serial, name, dtype, location, status, firmware, owner in DEVICES:
        devices[serial] = Device(
            serial_number=serial,
            name=name,
            device_type=dtype,
            location=location,
            status=status,
            firmware_version=firmware,
            owner_id=users[owner].id,
        )
    db.session.add_all(devices.values())
    db.session.flush()

    sensors, profiles = {}, {}
    for serial, name, stype, unit, low, high, base, noise in SENSORS:
        sensors[name] = Sensor(
            device_id=devices[serial].id,
            name=name,
            sensor_type=stype,
            unit=unit,
            min_value=low,
            max_value=high,
        )
        profiles[name] = (base, noise)
    db.session.add_all(sensors.values())
    db.session.flush()

    rules = [
        AlertRule(
            sensor_id=sensors[sensor_name].id,
            name=name,
            operator=op,
            threshold=threshold,
            severity=severity,
        )
        for sensor_name, name, op, threshold, severity in RULES
    ]
    db.session.add_all(rules)
    db.session.flush()

    # Pembacaan historis berurutan waktu; alert dibuat lewat service yang sama dengan API
    reading_count = 0
    for index in range(READINGS_PER_SENSOR):
        recorded_at = now - (READINGS_PER_SENSOR - 1 - index) * INTERVAL
        position_from_end = READINGS_PER_SENSOR - 1 - index
        for name, sensor in sensors.items():
            base, noise = profiles[name]
            value = SPIKES.get(name, {}).get(position_from_end)
            if value is None:
                value = round(rng.gauss(base, noise), 2)
            reading = TelemetryReading(
                sensor_id=sensor.id, value=value, recorded_at=recorded_at
            )
            db.session.add(reading)
            db.session.flush()
            evaluate_reading(reading)
            reading_count += 1

    for serial, device in devices.items():
        if device.status == "active":
            device.last_seen_at = now
        elif device.status == "maintenance":
            device.last_seen_at = now - timedelta(hours=26)

    # Variasi status alert: satu resolved, satu acknowledged, sisanya open
    alerts = db.session.scalars(select(Alert).order_by(Alert.id)).all()
    by_rule = {alert.rule.name: alert for alert in alerts}
    if "Tegangan UPS turun" in by_rule:
        update_status(by_rule["Tegangan UPS turun"], "resolved", users["budi"])
    if "Kelembapan tinggi" in by_rule:
        update_status(by_rule["Kelembapan tinggi"], "acknowledged", users["admin"])

    db.session.commit()
    return {
        "users": len(users),
        "devices": len(devices),
        "sensors": len(sensors),
        "alert_rules": len(rules),
        "telemetry_readings": reading_count,
        "alerts": len(alerts),
    }
