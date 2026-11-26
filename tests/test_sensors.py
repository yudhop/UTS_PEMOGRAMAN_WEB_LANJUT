import pytest

from .factories import create_device, create_reading, create_sensor

URL = "/api/v1/sensors"


@pytest.fixture()
def device(app):
    return create_device()


def payload(device, **overrides):
    data = {
        "device_id": device.id,
        "name": "Suhu Utama",
        "sensor_type": "temperature",
        "unit": "°C",
        "min_value": -40,
        "max_value": 125,
    }
    data.update(overrides)
    return data


def test_create_sensor_success(client, device):
    response = client.post(URL, json=payload(device))
    assert response.status_code == 201
    data = response.get_json()["data"]
    assert data["device_id"] == device.id
    assert data["max_value"] == 125.0


def test_create_sensor_rejects_inverted_range(client, device):
    response = client.post(URL, json=payload(device, min_value=50, max_value=10))
    assert response.status_code == 422
    assert "min_value" in response.get_json()["error"]["details"]


def test_create_sensor_unknown_device_is_422(client):
    response = client.post(URL, json={**payload(create_device()), "device_id": 999})
    assert response.status_code == 422
    assert "device_id" in response.get_json()["error"]["details"]


def test_sensor_name_unique_per_device_only(client, device):
    assert client.post(URL, json=payload(device)).status_code == 201
    assert client.post(URL, json=payload(device)).status_code == 409
    other = create_device()
    assert client.post(URL, json=payload(other)).status_code == 201


def test_patch_checks_range_against_stored_value(client, device):
    sensor = create_sensor(device, min_value=0.0, max_value=100.0)
    response = client.patch(f"{URL}/{sensor.id}", json={"min_value": 150})
    assert response.status_code == 422

    ok = client.patch(f"{URL}/{sensor.id}", json={"unit": "F"})
    assert ok.status_code == 200
    assert ok.get_json()["data"]["unit"] == "F"


def test_list_sensors_filters_and_search(client, device):
    create_sensor(device, name="Suhu A", sensor_type="temperature")
    create_sensor(device, name="Lembap A", sensor_type="humidity")
    create_sensor(create_device(), name="Suhu B", sensor_type="temperature")

    by_device = client.get(f"{URL}?device_id={device.id}").get_json()
    assert by_device["meta"]["total"] == 2
    by_type = client.get(f"{URL}?sensor_type=temperature&sort=-name").get_json()
    assert [s["name"] for s in by_type["data"]] == ["Suhu B", "Suhu A"]
    found = client.get(f"{URL}?q=lembap").get_json()
    assert [s["name"] for s in found["data"]] == ["Lembap A"]


def test_delete_sensor(client, device):
    sensor = create_sensor(device)
    assert client.delete(f"{URL}/{sensor.id}").status_code == 204
    assert client.get(f"{URL}/{sensor.id}").status_code == 404


def test_stats_summarise_readings(client, device):
    sensor = create_sensor(device)
    for value in (20.0, 30.0, 40.0):
        create_reading(sensor, value=value)

    data = client.get(f"{URL}/{sensor.id}/stats").get_json()["data"]
    assert (data["count"], data["min"], data["avg"], data["max"]) == (3, 20.0, 30.0, 40.0)
    assert data["latest"]["value"] == 40.0


def test_stats_without_readings_and_invalid_period(client, device):
    sensor = create_sensor(device)
    empty = client.get(f"{URL}/{sensor.id}/stats").get_json()["data"]
    assert empty["count"] == 0 and empty["avg"] is None and empty["latest"] is None

    bad = client.get(f"{URL}/{sensor.id}/stats?from=2026-02-01T00:00:00Z&to=2026-01-01T00:00:00Z")
    assert bad.status_code == 422
