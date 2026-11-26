import re
from pathlib import Path

import yaml

SPEC_PATH = Path(__file__).resolve().parent.parent / "docs" / "openapi.yaml"
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def _normalize(path):
    """/devices/<int:device_id> dan /devices/{device_id} -> /devices/{}"""
    return re.sub(r"<[^>]+>|\{[^}]+\}", "{}", path)


def test_openapi_spec_is_served(client):
    response = client.get("/openapi.yaml")
    assert response.status_code == 200
    spec = yaml.safe_load(response.data)
    assert spec["openapi"].startswith("3.")
    assert spec["info"]["title"] == "IoT Monitor API"


def test_swagger_ui_page_uses_nonce_csp(client):
    response = client.get("/docs")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "SwaggerUIBundle" in html
    nonce = re.search(r'<script nonce="([^"]+)">', html).group(1)
    assert f"'nonce-{nonce}'" in response.headers["Content-Security-Policy"]


def test_openapi_documents_every_api_route_and_nothing_else(app):
    spec = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
    documented = {
        (method.upper(), _normalize("/api/v1" + path))
        for path, item in spec["paths"].items()
        for method in item
        if method in HTTP_METHODS
    }
    actual = {
        (method, _normalize(rule.rule))
        for rule in app.url_map.iter_rules()
        if rule.rule.startswith("/api/v1")
        for method in rule.methods - {"HEAD", "OPTIONS"}
    }
    assert documented == actual
