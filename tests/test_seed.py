import pytest
from sqlalchemy import func, select

from app.extensions import db
from app.models import Alert, AlertRule, Device, Sensor, TelemetryReading, User
from seeds.seed import run_seed


@pytest.fixture()
def seeded(app):
    return run_seed()


def test_seed_populates_all_tables(seeded):
    assert seeded["users"] == 4
    assert seeded["devices"] == 5
    assert seeded["sensors"] == 7
    assert seeded["alert_rules"] == 5
    assert seeded["telemetry_readings"] == 7 * 48
    for model, key in (
        (User, "users"),
        (Device, "devices"),
        (Sensor, "sensors"),
        (AlertRule, "alert_rules"),
        (TelemetryReading, "telemetry_readings"),
    ):
        assert db.session.scalar(select(func.count()).select_from(model)) == seeded[key]


def test_seed_generates_alerts_with_mixed_statuses(seeded):
    statuses = set(db.session.scalars(select(Alert.status)))
    assert statuses == {"open", "acknowledged", "resolved"}


def test_seed_is_idempotent_and_resettable(app, seeded):
    assert run_seed() is None  # sudah terisi -> tidak menggandakan data
    again = run_seed(reset=True)
    assert again == seeded  # deterministik


def test_seed_cli_command(app):
    runner = app.test_cli_runner()
    first = runner.invoke(args=["seed"])
    assert first.exit_code == 0
    assert "Seed selesai" in first.output
    second = runner.invoke(args=["seed"])
    assert "sudah berisi data" in second.output


def test_seeded_data_is_served_by_api(app, seeded):
    client = app.test_client()
    devices = client.get("/api/v1/devices?per_page=100").get_json()
    assert devices["meta"]["total"] == 5
    open_alerts = client.get("/api/v1/alerts?status=open").get_json()
    assert open_alerts["meta"]["total"] >= 1
