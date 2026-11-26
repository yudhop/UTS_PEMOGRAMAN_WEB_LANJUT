from marshmallow import Schema, ValidationError, fields, validate, validates_schema

from ..constants import ALERT_STATUSES, SEVERITIES
from ..utils.pagination import PaginationSchema
from .base import UTCDateTime


class AlertSchema(Schema):
    """Representasi alert pada response (read-only)."""

    id = fields.Int(dump_only=True)
    rule_id = fields.Int(dump_only=True)
    sensor_id = fields.Int(attribute="rule.sensor_id", dump_only=True)
    device_id = fields.Int(attribute="rule.sensor.device_id", dump_only=True)
    reading_id = fields.Int(dump_only=True)
    severity = fields.Str(dump_only=True)
    message = fields.Str(dump_only=True)
    status = fields.Str(dump_only=True)
    triggered_at = UTCDateTime(dump_only=True)
    acknowledged_by_id = fields.Int(dump_only=True)
    acknowledged_at = UTCDateTime(dump_only=True)
    resolved_at = UTCDateTime(dump_only=True)


class AlertUpdateSchema(Schema):
    """Body PATCH /alerts/<id>: ubah status penanganan alert."""

    status = fields.Str(required=True, validate=validate.OneOf(ALERT_STATUSES))
    acknowledged_by_id = fields.Int(
        allow_none=True, load_default=None, strict=True, validate=validate.Range(min=1)
    )


class AlertQuerySchema(PaginationSchema):
    status = fields.Str(validate=validate.OneOf(ALERT_STATUSES))
    severity = fields.Str(validate=validate.OneOf(SEVERITIES))
    sensor_id = fields.Int(validate=validate.Range(min=1))
    device_id = fields.Int(validate=validate.Range(min=1))
    date_from = UTCDateTime(data_key="from")
    date_to = UTCDateTime(data_key="to")

    @validates_schema
    def check_period(self, data, **kwargs):
        if "date_from" in data and "date_to" in data and data["date_from"] > data["date_to"]:
            raise ValidationError("'from' must not be later than 'to'.", "from")
