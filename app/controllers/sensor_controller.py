"""Endpoint /sensors: pengelolaan sensor pada perangkat + statistik pembacaan."""
from flask import Blueprint, request
from sqlalchemy import func, select

from ..constants import API_PREFIX
from ..extensions import db
from ..models import Device, Sensor, TelemetryReading
from ..schemas.sensor_schema import SensorQuerySchema, SensorSchema, StatsQuerySchema
from ..schemas.telemetry_schema import TelemetrySchema
from ..utils.errors import ApiError
from ..utils.pagination import apply_sorting, contains, paginate
from ..utils.responses import created, no_content, success
from ..utils.validation import get_or_404, load_args, load_json, require_reference

bp = Blueprint("sensors", __name__, url_prefix=f"{API_PREFIX}/sensors")
sensor_schema = SensorSchema()
reading_schema = TelemetrySchema()

SORTABLE = {
    "name": Sensor.name,
    "sensor_type": Sensor.sensor_type,
    "created_at": Sensor.created_at,
}


def _ensure_unique_name(device_id, name, exclude_id=None):
    stmt = select(Sensor.id).where(Sensor.device_id == device_id, Sensor.name == name)
    if exclude_id is not None:
        stmt = stmt.where(Sensor.id != exclude_id)
    if db.session.scalar(stmt.limit(1)) is not None:
        raise ApiError(
            409,
            "CONFLICT",
            f"Sensor named '{name}' already exists on this device.",
            {"name": ["Must be unique per device."]},
        )


def _check_range(low, high):
    if low is not None and high is not None and low >= high:
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            "Input validation failed.",
            {"min_value": ["min_value must be less than max_value."]},
        )


@bp.post("")
def create_sensor():
    data = load_json(sensor_schema)
    require_reference(Device, data["device_id"], "device_id")
    _ensure_unique_name(data["device_id"], data["name"])

    sensor = Sensor(**data)
    db.session.add(sensor)
    db.session.commit()
    return created(sensor_schema.dump(sensor), "sensors.get_sensor", sensor_id=sensor.id)


@bp.get("")
def list_sensors():
    args = load_args(SensorQuerySchema())
    stmt = select(Sensor)
    if "q" in args:
        stmt = stmt.where(contains(Sensor.name, args["q"]))
    for field in ("device_id", "sensor_type"):
        if field in args:
            stmt = stmt.where(getattr(Sensor, field) == args[field])
    stmt = apply_sorting(stmt, SORTABLE, args["sort"], "name", Sensor.id)
    data, meta = paginate(stmt, sensor_schema, args)
    return success(data, meta=meta)


@bp.get("/<int:sensor_id>")
def get_sensor(sensor_id):
    return success(sensor_schema.dump(get_or_404(Sensor, sensor_id)))


@bp.route("/<int:sensor_id>", methods=["PUT", "PATCH"])
def update_sensor(sensor_id):
    """PUT = ganti seluruh field; PATCH = ubah sebagian field."""
    sensor = get_or_404(Sensor, sensor_id)
    data = load_json(sensor_schema, partial=request.method == "PATCH")
    if "device_id" in data:
        require_reference(Device, data["device_id"], "device_id")

    _ensure_unique_name(
        data.get("device_id", sensor.device_id),
        data.get("name", sensor.name),
        exclude_id=sensor.id,
    )
    _check_range(
        data.get("min_value", sensor.min_value), data.get("max_value", sensor.max_value)
    )

    for field, value in data.items():
        setattr(sensor, field, value)
    db.session.commit()
    return success(sensor_schema.dump(sensor))


@bp.delete("/<int:sensor_id>")
def delete_sensor(sensor_id):
    sensor = get_or_404(Sensor, sensor_id)
    db.session.delete(sensor)
    db.session.commit()
    return no_content()


@bp.get("/<int:sensor_id>/stats")
def sensor_stats(sensor_id):
    """Ringkasan pembacaan: jumlah, min, rata-rata, maks, dan pembacaan terakhir."""
    sensor = get_or_404(Sensor, sensor_id)
    args = load_args(StatsQuerySchema())

    conditions = [TelemetryReading.sensor_id == sensor.id]
    if "date_from" in args:
        conditions.append(TelemetryReading.recorded_at >= args["date_from"])
    if "date_to" in args:
        conditions.append(TelemetryReading.recorded_at <= args["date_to"])

    count, low, avg, high = db.session.execute(
        select(
            func.count(TelemetryReading.id),
            func.min(TelemetryReading.value),
            func.avg(TelemetryReading.value),
            func.max(TelemetryReading.value),
        ).where(*conditions)
    ).one()
    latest = db.session.scalar(
        select(TelemetryReading)
        .where(*conditions)
        .order_by(TelemetryReading.recorded_at.desc(), TelemetryReading.id.desc())
        .limit(1)
    )
    return success(
        {
            "sensor_id": sensor.id,
            "unit": sensor.unit,
            "count": count,
            "min": low,
            "avg": round(avg, 3) if avg is not None else None,
            "max": high,
            "latest": reading_schema.dump(latest) if latest else None,
        }
    )
