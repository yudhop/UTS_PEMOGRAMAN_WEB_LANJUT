"""Perilaku lintas-endpoint: health, format error, security header, API key."""
import pytest
from sqlalchemy.exc import IntegrityError

from app import create_app
from app.config import DEFAULT_SECRET_KEY, ProductionConfig, get_config


def test_health_check_ok(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.get_json()["data"]["status"] == "ok"


def test_root_returns_api_info(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.get_json()["data"]["base_url"] == "/api/v1"


def test_unknown_route_uses_consistent_error_format(client):
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    error = response.get_json()["error"]
    assert error["code"] == "NOT_FOUND"
    assert "message" in error


def test_method_not_allowed_sets_allow_header(client):
    response = client.post("/api/v1/health")
    assert response.status_code == 405
    assert response.get_json()["error"]["code"] == "METHOD_NOT_ALLOWED"
    assert "GET" in response.headers["Allow"]


def test_security_headers_present(client):
    headers = client.get("/api/v1/health").headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["Cache-Control"] == "no-store"
    assert "default-src 'none'" in headers["Content-Security-Policy"]


def test_write_requires_api_key_when_configured(app, client):
    app.config["API_KEY"] = "s3cret-key"

    no_key = client.post("/api/v1/health")
    assert no_key.status_code == 401
    assert no_key.get_json()["error"]["code"] == "UNAUTHORIZED"

    wrong_key = client.post("/api/v1/health", headers={"X-API-Key": "nope"})
    assert wrong_key.status_code == 401

    # Kunci benar lolos autentikasi (lalu 405 karena health hanya menerima GET)
    right_key = client.post("/api/v1/health", headers={"X-API-Key": "s3cret-key"})
    assert right_key.status_code == 405


def test_read_requests_do_not_need_api_key(app, client):
    app.config["API_KEY"] = "s3cret-key"
    assert client.get("/api/v1/health").status_code == 200


def test_unhandled_exception_returns_generic_500_without_leaking_details(app):
    @app.get("/boom")
    def boom():
        raise RuntimeError("password=hunter2 internal detail")

    response = app.test_client().get("/boom")
    assert response.status_code == 500
    error = response.get_json()["error"]
    assert error["code"] == "INTERNAL_SERVER_ERROR"
    assert "hunter2" not in response.get_data(as_text=True)


def test_integrity_error_is_translated_to_409(app):
    @app.get("/integrity")
    def integrity():
        raise IntegrityError("INSERT ...", {}, Exception("UNIQUE constraint failed: x.y"))

    response = app.test_client().get("/integrity")
    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "INTEGRITY_ERROR"
    assert "UNIQUE" not in response.get_data(as_text=True)  # detail DB tidak bocor


def test_production_refuses_default_secret_key(monkeypatch):
    monkeypatch.setattr(ProductionConfig, "SECRET_KEY", DEFAULT_SECRET_KEY)
    with pytest.raises(RuntimeError):
        create_app("production")


def test_unknown_config_name_is_rejected():
    with pytest.raises(ValueError):
        get_config("staging")
