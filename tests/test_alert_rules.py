import pytest

from .factories import create_rule, create_sensor

URL = "/api/v1/alert-rules"


@pytest.fixture()
def sensor(app):
    return create_sensor()


def payload(sensor, **overrides):
    data = {
        "sensor_id": sensor.id,
        "name": "Terlalu panas",
        "operator": "gt",
        "threshold": 35,
        "severity": "high",
    }
    data.update(overrides)
    return data


def test_create_rule_success_with_defaults(client, sensor):
    body = payload(sensor)
    del body["severity"]
    response = client.post(URL, json=body)
    assert response.status_code == 201
    data = response.get_json()["data"]
    assert data["severity"] == "medium"
    assert data["is_active"] is True


def test_create_rule_validation_errors(client, sensor):
    response = client.post(URL, json=payload(sensor, operator="between", threshold="panas"))
    assert response.status_code == 422
    assert {"operator", "threshold"} <= set(response.get_json()["error"]["details"])


def test_create_rule_unknown_sensor_is_422(client):
    response = client.post(URL, json={**payload(create_sensor()), "sensor_id": 999})
    assert response.status_code == 422


def test_filter_rules_by_active_flag_and_sensor(client, sensor):
    create_rule(sensor, is_active=True)
    create_rule(sensor, is_active=False)
    create_rule(create_sensor(), is_active=False)

    inactive = client.get(f"{URL}?is_active=false").get_json()
    assert inactive["meta"]["total"] == 2
    mine = client.get(f"{URL}?sensor_id={sensor.id}&is_active=false").get_json()
    assert mine["meta"]["total"] == 1


def test_patch_toggles_rule_and_delete(client, sensor):
    rule = create_rule(sensor)
    patched = client.patch(f"{URL}/{rule.id}", json={"is_active": False, "threshold": 40})
    assert patched.status_code == 200
    assert patched.get_json()["data"]["is_active"] is False
    assert client.put(f"{URL}/{rule.id}", json={"name": "x"}).status_code == 422
    assert client.delete(f"{URL}/{rule.id}").status_code == 204
    assert client.get(f"{URL}/{rule.id}").status_code == 404
