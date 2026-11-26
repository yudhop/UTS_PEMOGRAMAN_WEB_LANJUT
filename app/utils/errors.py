"""Format error response yang seragam untuk seluruh API.

Bentuk body error:
    {"error": {"code": "VALIDATION_ERROR", "message": "...", "details": {...}}}
"""
from flask import jsonify
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException, MethodNotAllowed

from ..extensions import db

CODE_BY_STATUS = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    413: "PAYLOAD_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    429: "TOO_MANY_REQUESTS",
}


class ApiError(Exception):
    """Error terkontrol yang diterjemahkan menjadi response JSON."""

    def __init__(self, status_code, code, message, details=None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


def error_response(status_code, code, message, details=None):
    body = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return jsonify(body), status_code


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def handle_api_error(exc):
        return error_response(exc.status_code, exc.code, exc.message, exc.details)

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc):
        status = exc.code or 500
        code = CODE_BY_STATUS.get(status, "HTTP_ERROR")
        response, status = error_response(status, code, exc.description)
        if isinstance(exc, MethodNotAllowed) and exc.valid_methods:
            response.headers["Allow"] = ", ".join(exc.valid_methods)
        return response, status

    @app.errorhandler(IntegrityError)
    def handle_integrity_error(exc):
        # Jaring pengaman (mis. race condition); detail DB tidak dibocorkan.
        db.session.rollback()
        app.logger.warning("Integrity error: %s", exc.orig)
        return error_response(
            409, "INTEGRITY_ERROR", "The request violates a data integrity constraint."
        )

    @app.errorhandler(Exception)
    def handle_unexpected(exc):
        db.session.rollback()
        app.logger.exception("Unhandled exception")
        return error_response(
            500, "INTERNAL_SERVER_ERROR", "An unexpected error occurred."
        )
