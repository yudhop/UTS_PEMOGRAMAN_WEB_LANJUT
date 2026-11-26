import pytest

from .factories import create_device, create_sensor, create_user

URL = "/api/v1/devices"


@pytest.fixture()
def owner(app):
    return create_user()


def payload(owner, **overrides):
    data = {
        "owner_id": owner.id,
        "name": "Node Gudang",
        "serial_number": "ESP32-0001",
        "device_type": "esp32",
        "location": "Gudang A",
    }
    data.update(overrides)
    return data


def test_create_device_success(client, owner):
    response = client.post(URL, json=payload(owner))
    assert response.status_code == 201
    data = response.get_json()["data"]
    assert response.headers["Location"] == f"{URL}/{data['id']}"
    assert data["status"] == "active"  # default
    assert data["last_seen_at"] is None
    assert data["created_at"].endswith("Z")


def test_create_device_validation_errors(client, owner):
    response = client.post(
        URL, json={"owner_id": owner.id, "device_type": "toaster", "id": 5, "name": "  "}
    )
    assert response.status_code == 422
    details = response.get_json()["error"]["details"]
    assert {"serial_number", "device_type", "id", "name"} <= set(details)


def test_create_device_rejects_non_json_content_type(client, owner):
    response = client.post(URL, data="name=x", content_type="text/plain")
    assert response.status_code == 415
    assert response.get_json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_create_device_rejects_malformed_json(client):
    response = client.post(URL, data="{bad json", content_type="application/json")
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "INVALID_JSON"


def test_create_device_unknown_owner_is_422(client):
    response = client.post(URL, json={**payload(create_user()), "owner_id": 999})
    assert response.status_code == 422
    assert "owner_id" in response.get_json()["error"]["details"]


def test_create_device_duplicate_serial_is_409(client, owner):
    assert client.post(URL, json=payload(owner)).status_code == 201
    response = client.post(URL, json=payload(owner, name="Lain"))
    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "CONFLICT"


def test_list_devices_pagination_filter_search_sort(client, owner):
    for i in range(5):
        create_device(owner, name=f"Alpha {i}", serial_number=f"AL-{i}")
    create_device(owner, name="Beta", serial_number="BE-1", status="maintenance")

    page = client.get(f"{URL}?per_page=4&page=2").get_json()
    assert page["meta"] == {"page": 2, "per_page": 4, "total": 6, "pages": 2}
    assert len(page["data"]) == 2

    maintenance = client.get(f"{URL}?status=maintenance").get_json()
    assert [d["name"] for d in maintenance["data"]] == ["Beta"]

    by_serial = client.get(f"{URL}?q=al-3").get_json()
    assert [d["serial_number"] for d in by_serial["data"]] == ["AL-3"]

    ascending = client.get(f"{URL}?sort=name&status=active").get_json()["data"]
    descending = client.get(f"{URL}?sort=-name&status=active").get_json()["data"]
    assert [d["name"] for d in ascending] == sorted(d["name"] for d in ascending)
    assert [d["name"] for d in descending] == [d["name"] for d in reversed(ascending)]


def test_search_treats_wildcards_literally(client, owner):
    create_device(owner, name="100% Aman", serial_number="W-1")
    create_device(owner, name="Biasa", serial_number="W-2")
    found = client.get(f"{URL}?q=%25").get_json()  # q = "%"
    assert [d["name"] for d in found["data"]] == ["100% Aman"]


@pytest.mark.parametrize(
    "query", ["sort=password", "per_page=1000", "page=0", "status=broken", "per_page=abc"]
)
def test_list_devices_rejects_invalid_query(client, query):
    response = client.get(f"{URL}?{query}")
    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_get_device_not_found(client):
    assert client.get(f"{URL}/999").status_code == 404


def test_patch_updates_only_given_fields(client, owner):
    device = create_device(owner, location="Lama")
    response = client.patch(f"{URL}/{device.id}", json={"status": "maintenance"})
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["status"] == "maintenance"
    assert data["location"] == "Lama"


def test_put_requires_full_payload(client, owner):
    device = create_device(owner)
    assert client.put(f"{URL}/{device.id}", json={"name": "Baru"}).status_code == 422

    full = payload(owner, name="Baru", serial_number=device.serial_number, status="inactive")
    response = client.put(f"{URL}/{device.id}", json=full)
    assert response.status_code == 200
    assert response.get_json()["data"]["status"] == "inactive"


def test_update_serial_to_existing_value_is_409(client, owner):
    first = create_device(owner)
    second = create_device(owner)
    response = client.patch(f"{URL}/{second.id}", json={"serial_number": first.serial_number})
    assert response.status_code == 409


def test_delete_device_removes_its_sensors(client, owner):
    sensor = create_sensor(create_device(owner))
    device_id, sensor_id = sensor.device_id, sensor.id  # ambil sebelum objek kedaluwarsa
    assert client.delete(f"{URL}/{device_id}").status_code == 204
    assert client.get(f"{URL}/{device_id}").status_code == 404
    assert client.get(f"/api/v1/sensors/{sensor_id}").status_code == 404
