"""Logika alert: evaluasi pembacaan terhadap aturan & siklus status alert."""
import operator

from sqlalchemy import select

from ..constants import ALERT_ACTIVE_STATUSES, ALERT_TRANSITIONS, RULE_OPERATORS
from ..extensions import db
from ..models import Alert, AlertRule
from ..models.base import utcnow
from ..utils.errors import ApiError

_COMPARATORS = {
    "gt": operator.gt,
    "gte": operator.ge,
    "lt": operator.lt,
    "lte": operator.le,
}


def _has_active_alert(rule_id):
    stmt = (
        select(Alert.id)
        .where(Alert.rule_id == rule_id, Alert.status.in_(ALERT_ACTIVE_STATUSES))
        .limit(1)
    )
    return db.session.scalar(stmt) is not None


def _build_message(reading, rule):
    sensor = reading.sensor
    unit = sensor.unit
    text = (
        f"{sensor.name} on {sensor.device.name}: reading {reading.value:g} {unit} "
        f"violates rule '{rule.name}' ({RULE_OPERATORS[rule.operator]} {rule.threshold:g} {unit})"
    )
    return text[:255]


def evaluate_reading(reading):
    """Buat alert untuk setiap aturan aktif yang dilanggar oleh `reading`.

    Satu aturan hanya punya satu alert aktif (open/acknowledged) pada satu waktu,
    sehingga sensor yang terus melewati ambang tidak membanjiri tabel alert.
    """
    rules = db.session.scalars(
        select(AlertRule)
        .where(AlertRule.sensor_id == reading.sensor_id, AlertRule.is_active.is_(True))
        .order_by(AlertRule.id)
    ).all()

    created = []
    for rule in rules:
        if not _COMPARATORS[rule.operator](reading.value, rule.threshold):
            continue
        if _has_active_alert(rule.id):
            continue
        alert = Alert(
            rule=rule,
            reading=reading,
            severity=rule.severity,
            message=_build_message(reading, rule),
            triggered_at=reading.recorded_at,
        )
        db.session.add(alert)
        created.append(alert)
    db.session.flush()
    return created


def update_status(alert, new_status, acknowledged_by=None):
    """Ubah status alert mengikuti transisi open -> acknowledged -> resolved."""
    if new_status not in ALERT_TRANSITIONS[alert.status]:
        raise ApiError(
            409,
            "INVALID_STATE_TRANSITION",
            f"Cannot change alert status from '{alert.status}' to '{new_status}'.",
        )
    now = utcnow()
    if new_status == "acknowledged":
        alert.acknowledged_at = now
    else:
        alert.resolved_at = now
    if acknowledged_by is not None:
        alert.acknowledged_by = acknowledged_by
    alert.status = new_status
    return alert
