"""Endpoint /alerts: melihat dan menangani alert."""
from flask import Blueprint
from sqlalchemy import select
from sqlalchemy.orm import contains_eager

from ..constants import API_PREFIX
from ..extensions import db
from ..models import Alert, AlertRule, Sensor, User
from ..schemas.alert_schema import AlertQuerySchema, AlertSchema, AlertUpdateSchema
from ..services import alert_service
from ..utils.pagination import apply_sorting, paginate
from ..utils.responses import success
from ..utils.validation import get_or_404, load_args, load_json, require_reference

bp = Blueprint("alerts", __name__, url_prefix=f"{API_PREFIX}/alerts")
alert_schema = AlertSchema()
update_schema = AlertUpdateSchema()

SORTABLE = {
    "triggered_at": Alert.triggered_at,
    "status": Alert.status,
}


@bp.get("")
def list_alerts():
    args = load_args(AlertQuerySchema())
    # JOIN + contains_eager: sensor_id/device_id di response tanpa query tambahan per baris
    stmt = (
        select(Alert)
        .join(Alert.rule)
        .join(AlertRule.sensor)
        .options(contains_eager(Alert.rule).contains_eager(AlertRule.sensor))
    )
    for field in ("status", "severity"):
        if field in args:
            stmt = stmt.where(getattr(Alert, field) == args[field])
    if "sensor_id" in args:
        stmt = stmt.where(AlertRule.sensor_id == args["sensor_id"])
    if "device_id" in args:
        stmt = stmt.where(Sensor.device_id == args["device_id"])
    if "date_from" in args:
        stmt = stmt.where(Alert.triggered_at >= args["date_from"])
    if "date_to" in args:
        stmt = stmt.where(Alert.triggered_at <= args["date_to"])
    stmt = apply_sorting(stmt, SORTABLE, args["sort"], "-triggered_at", Alert.id)
    data, meta = paginate(stmt, alert_schema, args)
    return success(data, meta=meta)


@bp.get("/<int:alert_id>")
def get_alert(alert_id):
    return success(alert_schema.dump(get_or_404(Alert, alert_id)))


@bp.patch("/<int:alert_id>")
def update_alert(alert_id):
    """Ubah status alert: open -> acknowledged -> resolved."""
    alert = get_or_404(Alert, alert_id)
    data = load_json(update_schema)
    user = None
    if data["acknowledged_by_id"] is not None:
        user = require_reference(User, data["acknowledged_by_id"], "acknowledged_by_id")
    alert_service.update_status(alert, data["status"], user)
    db.session.commit()
    return success(alert_schema.dump(alert))
