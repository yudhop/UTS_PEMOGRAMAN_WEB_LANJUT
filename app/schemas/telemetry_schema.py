from datetime import timedelta

from marshmallow import Schema, ValidationError, fields, validate, validates, validates_schema

from ..constants import FUTURE_TOLERANCE_MINUTES
from ..models.base import utcnow
from ..utils.pagination import PaginationSchema
from .base import UTCDateTime


class TelemetrySchema(Schema):
    id = fields.Int(dump_only=True)
    sensor_id = fields.Int(required=True, strict=True, validate=validate.Range(min=1))
    value = fields.Float(required=True, allow_nan=False)
    # Opsional: bila kosong, server memakai waktu saat request diterima
    recorded_at = UTCDateTime(allow_none=True, load_default=None)
    created_at = UTCDateTime(dump_only=True)

    @validates("recorded_at")
    def not_in_future(self, value, **kwargs):
        limit = utcnow() + timedelta(minutes=FUTURE_TOLERANCE_MINUTES)
        if value is not None and value > limit:
            raise ValidationError("recorded_at must not be in the future.")


class TelemetryQuerySchema(PaginationSchema):
    sensor_id = fields.Int(validate=validate.Range(min=1))
    device_id = fields.Int(validate=validate.Range(min=1))
    date_from = UTCDateTime(data_key="from")
    date_to = UTCDateTime(data_key="to")

    @validates_schema
    def check_period(self, data, **kwargs):
        if "date_from" in data and "date_to" in data and data["date_from"] > data["date_to"]:
            raise ValidationError("'from' must not be later than 'to'.", "from")
