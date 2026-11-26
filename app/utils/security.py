"""Praktik keamanan dasar: security header dan API key opsional untuk request tulis."""
import hmac

from flask import request

from .errors import ApiError

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
}


def register_security(app):
    @app.before_request
    def require_api_key_for_writes():
        expected = app.config.get("API_KEY")
        if not expected or request.method in SAFE_METHODS:
            return None
        provided = request.headers.get("X-API-Key", "")
        if not hmac.compare_digest(provided.encode(), expected.encode()):
            raise ApiError(401, "UNAUTHORIZED", "Missing or invalid API key.")
        return None

    @app.after_request
    def add_security_headers(response):
        for header, value in SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        return response
