from marshmallow import Schema, ValidationError, fields, post_load, validate

from ..constants import USER_ROLES
from ..utils.pagination import PaginationSchema
from .base import Text, UTCDateTime


def _password_strength(value):
    if not (any(c.isalpha() for c in value) and any(c.isdigit() for c in value)):
        raise ValidationError("Password must contain at least one letter and one digit.")


class UserSchema(Schema):
    id = fields.Int(dump_only=True)
    username = Text(
        required=True,
        validate=[
            validate.Length(min=3, max=50),
            validate.Regexp(
                r"^[A-Za-z0-9_.-]+$",
                error="Only letters, digits, '_', '.' and '-' are allowed.",
            ),
        ],
    )
    email = fields.Email(required=True, validate=validate.Length(max=120))
    # load_only: password tidak pernah ikut di response
    password = fields.Str(
        required=True,
        load_only=True,
        validate=[validate.Length(min=8, max=128), _password_strength],
    )
    role = fields.Str(load_default="operator", validate=validate.OneOf(USER_ROLES))
    created_at = UTCDateTime(dump_only=True)

    @post_load
    def normalize(self, data, **kwargs):
        data["username"] = data["username"].lower()
        data["email"] = data["email"].lower()
        return data


class UserQuerySchema(PaginationSchema):
    q = fields.Str(validate=validate.Length(min=1, max=100))
    role = fields.Str(validate=validate.OneOf(USER_ROLES))
