"""Menyajikan spesifikasi OpenAPI dan Swagger UI (halaman /docs)."""
import secrets

from flask import Blueprint, Response, send_from_directory

from ..config import BASE_DIR

bp = Blueprint("docs", __name__)

DOCS_DIR = BASE_DIR / "docs"
SWAGGER_CDN = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5"

PAGE = """<!doctype html>
<html lang="id">
<head>
  <meta charset="utf-8">
  <title>IoT Monitor API - Docs</title>
  <link rel="stylesheet" href="{cdn}/swagger-ui.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="{cdn}/swagger-ui-bundle.js"></script>
  <script nonce="{nonce}">
    window.ui = SwaggerUIBundle({{ url: "/openapi.yaml", dom_id: "#swagger-ui" }});
  </script>
</body>
</html>
"""


@bp.get("/openapi.yaml")
def openapi_spec():
    return send_from_directory(DOCS_DIR, "openapi.yaml", mimetype="application/yaml")


@bp.get("/docs")
def swagger_ui():
    nonce = secrets.token_urlsafe(16)
    response = Response(PAGE.format(cdn=SWAGGER_CDN, nonce=nonce), mimetype="text/html")
    # CSP khusus halaman ini: izinkan Swagger UI dari CDN dan satu inline script ber-nonce
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; "
        f"script-src https://cdn.jsdelivr.net 'nonce-{nonce}'; "
        "style-src https://cdn.jsdelivr.net 'unsafe-inline'; "
        "img-src 'self' data: https:; font-src https://cdn.jsdelivr.net; "
        "connect-src 'self'; frame-ancestors 'none'"
    )
    return response
