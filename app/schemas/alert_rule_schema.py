from marshmallow import Schema, fields, validate

from ..constants import RULE_OPERATORS, SEVERITIES
from ..utils.pagination import PaginationSchema
from .base import Text, UTCDateTime


class AlertRuleSchema(Schema):
    id = fields.Int(dump_only=True)
    sensor_id = fields.Int(required=True, strict=True, validate=validate.Range(min=1))
    name = Text(required=True, validate=validate.Length(min=1, max=100))
    operator = fields.Str(required=True, validate=validate.OneOf(tuple(RULE_OPERATORS)))
    threshold = fields.Float(required=True, allow_nan=False)
    severity = fields.Str(load_default="medium", validate=validate.OneOf(SEVERITIES))
    is_active = fields.Bool(load_default=True)
    created_at = UTCDateTime(dump_only=True)
    updated_at = UTCDateTime(dump_only=True)


class AlertRuleQuerySchema(PaginationSchema):
    sensor_id = fields.Int(validate=validate.Range(min=1))
    severity = fields.Str(validate=validate.OneOf(SEVERITIES))
    is_active = fields.Bool()
