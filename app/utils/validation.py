"""Helper validasi input pada batas kepercayaan (request body & query string)."""
from flask import request
from marshmallow import ValidationError
from sqlalchemy import select

from ..extensions import db
from .errors import ApiError


def _validation_error(details):
    return ApiError(422, "VALIDATION_ERROR", "Input validation failed.", details)


def load_json(schema, *, partial=False):
    """Validasi body JSON dengan schema; error -> 415 / 400 / 422."""
    if not request.is_json:
        raise ApiError(
            415, "UNSUPPORTED_MEDIA_TYPE", "Content-Type must be application/json."
        )
    payload = request.get_json(silent=True)
    if payload is None:
        raise ApiError(400, "INVALID_JSON", "Request body is not valid JSON.")
    try:
        return schema.load(payload, partial=partial)
    except ValidationError as exc:
        raise _validation_error(exc.messages) from exc


def load_args(schema):
    """Validasi query string dengan schema; error -> 422."""
    try:
        return schema.load(request.args.to_dict())
    except ValidationError as exc:
        raise _validation_error(exc.messages) from exc


def get_or_404(model, pk):
    obj = db.session.get(model, pk)
    if obj is None:
        raise ApiError(404, "NOT_FOUND", f"{model.__name__} with id {pk} was not found.")
    return obj


def require_reference(model, pk, field):
    """Pastikan foreign key di body menunjuk data yang ada (jika tidak -> 422)."""
    obj = db.session.get(model, pk)
    if obj is None:
        raise _validation_error({field: [f"{model.__name__} with id {pk} does not exist."]})
    return obj


def ensure_unique(model, field, value, *, exclude_id=None):
    """Tolak nilai duplikat pada kolom unik dengan 409 (sebelum menyentuh DB constraint)."""
    stmt = select(model.id).where(getattr(model, field) == value)
    if exclude_id is not None:
        stmt = stmt.where(model.id != exclude_id)
    if db.session.scalar(stmt.limit(1)) is not None:
        raise ApiError(
            409,
            "CONFLICT",
            f"{model.__name__} with {field} '{value}' already exists.",
            {field: ["Must be unique."]},
        )
