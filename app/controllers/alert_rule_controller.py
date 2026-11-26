"""Endpoint /alert-rules: aturan ambang batas per sensor."""
from flask import Blueprint, request
from sqlalchemy import select

from ..constants import API_PREFIX
from ..extensions import db
from ..models import AlertRule, Sensor
from ..schemas.alert_rule_schema import AlertRuleQuerySchema, AlertRuleSchema
from ..utils.pagination import apply_sorting, paginate
from ..utils.responses import created, no_content, success
from ..utils.validation import get_or_404, load_args, load_json, require_reference

bp = Blueprint("alert_rules", __name__, url_prefix=f"{API_PREFIX}/alert-rules")
rule_schema = AlertRuleSchema()

SORTABLE = {
    "name": AlertRule.name,
    "threshold": AlertRule.threshold,
    "created_at": AlertRule.created_at,
}


@bp.post("")
def create_rule():
    data = load_json(rule_schema)
    require_reference(Sensor, data["sensor_id"], "sensor_id")
    rule = AlertRule(**data)
    db.session.add(rule)
    db.session.commit()
    return created(rule_schema.dump(rule), "alert_rules.get_rule", rule_id=rule.id)


@bp.get("")
def list_rules():
    args = load_args(AlertRuleQuerySchema())
    stmt = select(AlertRule)
    for field in ("sensor_id", "severity", "is_active"):
        if field in args:
            stmt = stmt.where(getattr(AlertRule, field) == args[field])
    stmt = apply_sorting(stmt, SORTABLE, args["sort"], "-created_at", AlertRule.id)
    data, meta = paginate(stmt, rule_schema, args)
    return success(data, meta=meta)


@bp.get("/<int:rule_id>")
def get_rule(rule_id):
    return success(rule_schema.dump(get_or_404(AlertRule, rule_id)))


@bp.route("/<int:rule_id>", methods=["PUT", "PATCH"])
def update_rule(rule_id):
    """PUT = ganti seluruh field; PATCH = ubah sebagian field."""
    rule = get_or_404(AlertRule, rule_id)
    data = load_json(rule_schema, partial=request.method == "PATCH")
    if "sensor_id" in data:
        require_reference(Sensor, data["sensor_id"], "sensor_id")
    for field, value in data.items():
        setattr(rule, field, value)
    db.session.commit()
    return success(rule_schema.dump(rule))


@bp.delete("/<int:rule_id>")
def delete_rule(rule_id):
    rule = get_or_404(AlertRule, rule_id)
    db.session.delete(rule)
    db.session.commit()
    return no_content()
