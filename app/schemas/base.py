"""Field kustom yang dipakai bersama oleh semua schema."""
from datetime import timezone

from marshmallow import fields


class Text(fields.String):
    """String yang dipangkas (strip); string kosong/spasi saja gagal di Length(min=1)."""

    def _deserialize(self, value, attr, data, **kwargs):
        return super()._deserialize(value, attr, data, **kwargs).strip()


class UTCDateTime(fields.DateTime):
    """Datetime ISO 8601. Input berzona waktu dikonversi ke UTC; output berakhiran 'Z'."""

    def __init__(self, **kwargs):
        super().__init__(format="iso", **kwargs)

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value.isoformat(timespec="milliseconds") + "Z"

    def _deserialize(self, value, attr, data, **kwargs):
        parsed = super()._deserialize(value, attr, data, **kwargs)
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
