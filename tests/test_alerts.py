import pytest

from .factories import create_rule, create_sensor, create_user

URL = "/api/v1/alerts"
TELEMETRY = "/api/v1/telemetry"


def trigger(client, sensor, value=50.0):
    response = client.post(TELEMETRY, json={"sensor_id": sensor.id, "value": value})
    assert response.status_code == 201
    return response.get_json()["data"]["triggered_alerts"][0]


@pytest.fixture()
def sensor(app):
    sensor = create_sensor()
    create_rule(sensor, operator="gt", threshold=30.0, severity="critical")
    return sensor


def test_list_and_filter_alerts(client, sensor):
    alert = trigger(client, sensor)
    quiet_sensor = create_sensor()
    create_rule(quiet_sensor, severity="low")
    trigger(client, quiet_sensor)

    everything = client.get(URL).get_json()
    assert everything["meta"]["total"] == 2

    critical = client.get(f"{URL}?severity=critical").get_json()["data"]
    assert [a["id"] for a in critical] == [alert["id"]]
    assert critical[0]["sensor_id"] == sensor.id
    assert critical[0]["device_id"] == sensor.device_id

    by_device = client.get(f"{URL}?device_id={sensor.device_id}").get_json()
    assert by_device["meta"]["total"] == 1
    assert client.get(f"{URL}?status=resolved").get_json()["meta"]["total"] == 0


def test_alert_lifecycle_acknowledge_then_resolve(client, sensor):
    alert = trigger(client, sensor)
    user = create_user()

    acked = client.patch(
        f"{URL}/{alert['id']}", json={"status": "acknowledged", "acknowledged_by_id": user.id}
    )
    assert acked.status_code == 200
    data = acked.get_json()["data"]
    assert data["status"] == "acknowledged"
    assert data["acknowledged_by_id"] == user.id
    assert data["acknowledged_at"] is not None

    resolved = client.patch(f"{URL}/{alert['id']}", json={"status": "resolved"})
    assert resolved.status_code == 200
    assert resolved.get_json()["data"]["resolved_at"] is not None


def test_invalid_transitions_are_409(client, sensor):
    alert = trigger(client, sensor)
    same = client.patch(f"{URL}/{alert['id']}", json={"status": "open"})
    assert same.status_code == 409
    assert same.get_json()["error"]["code"] == "INVALID_STATE_TRANSITION"

    client.patch(f"{URL}/{alert['id']}", json={"status": "resolved"})
    reopened = client.patch(f"{URL}/{alert['id']}", json={"status": "acknowledged"})
    assert reopened.status_code == 409


def test_update_alert_validation(client, sensor):
    alert = trigger(client, sensor)
    bad_status = client.patch(f"{URL}/{alert['id']}", json={"status": "ignored"})
    assert bad_status.status_code == 422

    unknown_user = client.patch(
        f"{URL}/{alert['id']}", json={"status": "acknowledged", "acknowledged_by_id": 999}
    )
    assert unknown_user.status_code == 422
    assert "acknowledged_by_id" in unknown_user.get_json()["error"]["details"]


def test_resolved_alert_allows_new_alert_for_same_rule(client, sensor):
    first = trigger(client, sensor, value=50)
    client.patch(f"{URL}/{first['id']}", json={"status": "resolved"})
    second = trigger(client, sensor, value=55)
    assert second["id"] != first["id"]


def test_get_alert_not_found(client):
    assert client.get(f"{URL}/999").status_code == 404


def test_alerts_sorted_by_trigger_time(client, sensor):
    first = trigger(client, sensor)
    other = create_sensor()
    create_rule(other)
    second = trigger(client, other)

    newest_first = client.get(URL).get_json()["data"]
    assert [a["id"] for a in newest_first] == [second["id"], first["id"]]
    oldest_first = client.get(f"{URL}?sort=triggered_at").get_json()["data"]
    assert [a["id"] for a in oldest_first] == [first["id"], second["id"]]
