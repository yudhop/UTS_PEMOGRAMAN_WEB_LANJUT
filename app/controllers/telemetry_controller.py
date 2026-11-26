"""Endpoint /telemetry: penerimaan dan pencarian pembacaan sensor."""
from flask import Blueprint
from sqlalchemy import select

from ..constants import API_PREFIX
from ..extensions import db
from ..models import Sensor, TelemetryReading
from ..schemas.alert_schema import AlertSchema
from ..schemas.telemetry_schema import TelemetryQuerySchema, TelemetrySchema
from ..services.telemetry_service import ingest_reading
from ..utils.pagination import apply_sorting, paginate
from ..utils.responses import created, no_content, success
from ..utils.validation import get_or_404, load_args, load_json, require_reference

bp = Blueprint("telemetry", __name__, url_prefix=f"{API_PREFIX}/telemetry")
reading_schema = TelemetrySchema()
alert_schema = AlertSchema()

SORTABLE = {
    "recorded_at": TelemetryReading.recorded_at,
    "value": TelemetryReading.value,
}


@bp.post("")
def create_reading():
    """Terima satu pembacaan; response menyertakan alert yang terpicu (jika ada)."""
    data = load_json(reading_schema)
    sensor = require_reference(Sensor, data["sensor_id"], "sensor_id")
    reading, alerts = ingest_reading(sensor, data["value"], data["recorded_at"])

    body = reading_schema.dump(reading)
    body["triggered_alerts"] = alert_schema.dump(alerts, many=True)
    return created(body, "telemetry.get_reading", reading_id=reading.id)


@bp.get("")
def list_readings():
    args = load_args(TelemetryQuerySchema())
    stmt = select(TelemetryReading)
    if "device_id" in args:
        stmt = stmt.join(Sensor, Sensor.id == TelemetryReading.sensor_id).where(
            Sensor.device_id == args["device_id"]
        )
    if "sensor_id" in args:
        stmt = stmt.where(TelemetryReading.sensor_id == args["sensor_id"])
    if "date_from" in args:
        stmt = stmt.where(TelemetryReading.recorded_at >= args["date_from"])
    if "date_to" in args:
        stmt = stmt.where(TelemetryReading.recorded_at <= args["date_to"])
    stmt = apply_sorting(stmt, SORTABLE, args["sort"], "-recorded_at", TelemetryReading.id)
    data, meta = paginate(stmt, reading_schema, args)
    return success(data, meta=meta)


@bp.get("/<int:reading_id>")
def get_reading(reading_id):
    return success(reading_schema.dump(get_or_404(TelemetryReading, reading_id)))


@bp.delete("/<int:reading_id>")
def delete_reading(reading_id):
    reading = get_or_404(TelemetryReading, reading_id)
    db.session.delete(reading)  # alert terkait tetap ada (reading_id jadi NULL)
    db.session.commit()
    return no_content()
