import pytest

from .factories import create_device, create_reading, create_rule, create_sensor

URL = "/api/v1/telemetry"


@pytest.fixture()
def sensor(app):
    return create_sensor(min_value=-40.0, max_value=125.0)


def test_post_reading_success_updates_device_last_seen(client, sensor):
    response = client.post(URL, json={"sensor_id": sensor.id, "value": 27.5})
    assert response.status_code == 201
    data = response.get_json()["data"]
    assert data["value"] == 27.5
    assert data["triggered_alerts"] == []
    assert response.headers["Location"] == f"{URL}/{data['id']}"

    device = client.get(f"/api/v1/devices/{sensor.device_id}").get_json()["data"]
    assert device["last_seen_at"] is not None


def test_recorded_at_with_timezone_is_converted_to_utc(client, sensor):
    response = client.post(
        URL,
        json={"sensor_id": sensor.id, "value": 20, "recorded_at": "2026-01-01T07:00:00+07:00"},
    )
    assert response.status_code == 201
    assert response.get_json()["data"]["recorded_at"] == "2026-01-01T00:00:00.000Z"


def test_value_outside_sensor_range_is_rejected(client, sensor):
    response = client.post(URL, json={"sensor_id": sensor.id, "value": 500})
    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "VALUE_OUT_OF_RANGE"


@pytest.mark.parametrize(
    "body",
    [
        {"sensor_id": 1, "value": "panas"},
        {"sensor_id": 1},
        {"sensor_id": "1", "value": 1},
        {"sensor_id": 1, "value": True},
        {"sensor_id": 1, "value": 1, "recorded_at": "kemarin"},
    ],
)
def test_invalid_payloads_are_422(client, sensor, body):
    response = client.post(URL, json=body)
    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_nan_value_is_rejected(client, sensor):
    raw = f'{{"sensor_id": {sensor.id}, "value": NaN}}'
    response = client.post(URL, data=raw, content_type="application/json")
    assert response.status_code == 422


def test_future_timestamp_is_rejected(client, sensor):
    response = client.post(
        URL, json={"sensor_id": sensor.id, "value": 1, "recorded_at": "2999-01-01T00:00:00Z"}
    )
    assert response.status_code == 422
    assert "recorded_at" in response.get_json()["error"]["details"]


def test_unknown_sensor_is_422(client):
    response = client.post(URL, json={"sensor_id": 999, "value": 1})
    assert response.status_code == 422
    assert "sensor_id" in response.get_json()["error"]["details"]


@pytest.mark.parametrize("status", ["inactive", "maintenance"])
def test_inactive_device_cannot_send_telemetry(client, status):
    sensor = create_sensor(create_device(status=status))
    response = client.post(URL, json={"sensor_id": sensor.id, "value": 20})
    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "DEVICE_NOT_ACTIVE"


def test_reading_that_violates_rule_triggers_one_alert(client, sensor):
    create_rule(sensor, operator="gt", threshold=30.0, severity="high")

    first = client.post(URL, json={"sensor_id": sensor.id, "value": 35.0})
    alerts = first.get_json()["data"]["triggered_alerts"]
    assert len(alerts) == 1
    assert alerts[0]["severity"] == "high"
    assert alerts[0]["status"] == "open"
    assert "35" in alerts[0]["message"]

    # Aturan yang sama tidak membuat alert ganda selama alert sebelumnya belum selesai
    second = client.post(URL, json={"sensor_id": sensor.id, "value": 36.0})
    assert second.get_json()["data"]["triggered_alerts"] == []


def test_inactive_rule_does_not_trigger(client, sensor):
    create_rule(sensor, operator="gt", threshold=30.0, is_active=False)
    response = client.post(URL, json={"sensor_id": sensor.id, "value": 99})
    assert response.get_json()["data"]["triggered_alerts"] == []


@pytest.mark.parametrize(
    "operator,threshold,value,triggered",
    [("gte", 30, 30, True), ("gt", 30, 30, False), ("lt", 10, 5, True), ("lte", 10, 11, False)],
)
def test_rule_operators(client, sensor, operator, threshold, value, triggered):
    create_rule(sensor, operator=operator, threshold=float(threshold))
    response = client.post(URL, json={"sensor_id": sensor.id, "value": value})
    assert bool(response.get_json()["data"]["triggered_alerts"]) is triggered


def test_list_readings_filters_sorting_and_pagination(client, sensor):
    other = create_sensor()
    for index, value in enumerate((10.0, 20.0, 30.0, 40.0)):
        create_reading(sensor, value=value)
    create_reading(other, value=99.0)

    newest_first = client.get(f"{URL}?sensor_id={sensor.id}").get_json()
    assert [r["value"] for r in newest_first["data"]] == [40.0, 30.0, 20.0, 10.0]

    by_value = client.get(f"{URL}?sensor_id={sensor.id}&sort=value&per_page=2&page=2").get_json()
    assert [r["value"] for r in by_value["data"]] == [30.0, 40.0]
    assert by_value["meta"]["total"] == 4

    by_device = client.get(f"{URL}?device_id={other.device_id}").get_json()
    assert by_device["meta"]["total"] == 1


def test_list_readings_time_window(client, sensor):
    from datetime import datetime

    for day in (1, 2, 3):
        create_reading(sensor, value=float(day), recorded_at=datetime(2026, 1, day, 12, 0, 0))

    window = client.get(
        f"{URL}?sensor_id={sensor.id}&from=2026-01-02T00:00:00Z&to=2026-01-02T23:59:59Z"
    ).get_json()
    assert [r["value"] for r in window["data"]] == [2.0]

    reversed_window = client.get(f"{URL}?from=2026-02-01T00:00:00Z&to=2026-01-01T00:00:00Z")
    assert reversed_window.status_code == 422


def test_get_and_delete_reading(client, sensor):
    reading = create_reading(sensor)
    reading_id = reading.id
    assert client.get(f"{URL}/{reading_id}").status_code == 200
    assert client.delete(f"{URL}/{reading_id}").status_code == 204
    assert client.get(f"{URL}/{reading_id}").status_code == 404


def test_deleting_reading_keeps_alert_history(client, sensor):
    create_rule(sensor, operator="gt", threshold=30.0)
    created = client.post(URL, json={"sensor_id": sensor.id, "value": 50}).get_json()["data"]

    assert client.delete(f"{URL}/{created['id']}").status_code == 204
    alert = client.get(f"/api/v1/alerts/{created['triggered_alerts'][0]['id']}").get_json()["data"]
    assert alert["reading_id"] is None
