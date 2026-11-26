from marshmallow import EXCLUDE, Schema, ValidationError, fields, validate, validates_schema

from ..constants import SENSOR_TYPES
from ..utils.pagination import PaginationSchema
from .base import Text, UTCDateTime


class SensorSchema(Schema):
    id = fields.Int(dump_only=True)
    device_id = fields.Int(required=True, strict=True, validate=validate.Range(min=1))
    name = Text(required=True, validate=validate.Length(min=1, max=100))
    sensor_type = fields.Str(required=True, validate=validate.OneOf(SENSOR_TYPES))
    unit = Text(required=True, validate=validate.Length(min=1, max=20))
    min_value = fields.Float(allow_none=True, load_default=None, allow_nan=False)
    max_value = fields.Float(allow_none=True, load_default=None, allow_nan=False)
    created_at = UTCDateTime(dump_only=True)
    updated_at = UTCDateTime(dump_only=True)

    @validates_schema
    def check_range(self, data, **kwargs):
        low, high = data.get("min_value"), data.get("max_value")
        if low is not None and high is not None and low >= high:
            raise ValidationError("min_value must be less than max_value.", "min_value")


class SensorQuerySchema(PaginationSchema):
    q = fields.Str(validate=validate.Length(min=1, max=100))
    device_id = fields.Int(validate=validate.Range(min=1))
    sensor_type = fields.Str(validate=validate.OneOf(SENSOR_TYPES))


class StatsQuerySchema(Schema):
    class Meta:
        unknown = EXCLUDE

    date_from = UTCDateTime(data_key="from")
    date_to = UTCDateTime(data_key="to")

    @validates_schema
    def check_period(self, data, **kwargs):
        if "date_from" in data and "date_to" in data and data["date_from"] > data["date_to"]:
            raise ValidationError("'from' must not be later than 'to'.", "from")
