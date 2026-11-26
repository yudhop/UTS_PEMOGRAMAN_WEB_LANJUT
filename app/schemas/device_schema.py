from marshmallow import Schema, fields, validate

from ..constants import DEVICE_STATUSES, DEVICE_TYPES
from ..utils.pagination import PaginationSchema
from .base import Text, UTCDateTime


class DeviceSchema(Schema):
    id = fields.Int(dump_only=True)
    owner_id = fields.Int(required=True, strict=True, validate=validate.Range(min=1))
    name = Text(required=True, validate=validate.Length(min=1, max=100))
    serial_number = Text(
        required=True,
        validate=[
            validate.Length(min=3, max=64),
            validate.Regexp(
                r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$",
                error="Only letters, digits, '_', '.', ':' and '-' are allowed.",
            ),
        ],
    )
    device_type = fields.Str(required=True, validate=validate.OneOf(DEVICE_TYPES))
    location = Text(allow_none=True, load_default=None, validate=validate.Length(max=120))
    status = fields.Str(load_default="active", validate=validate.OneOf(DEVICE_STATUSES))
    firmware_version = Text(
        allow_none=True, load_default=None, validate=validate.Length(max=30)
    )
    last_seen_at = UTCDateTime(dump_only=True)
    created_at = UTCDateTime(dump_only=True)
    updated_at = UTCDateTime(dump_only=True)


class DeviceQuerySchema(PaginationSchema):
    q = fields.Str(validate=validate.Length(min=1, max=100))
    status = fields.Str(validate=validate.OneOf(DEVICE_STATUSES))
    device_type = fields.Str(validate=validate.OneOf(DEVICE_TYPES))
    owner_id = fields.Int(validate=validate.Range(min=1))
