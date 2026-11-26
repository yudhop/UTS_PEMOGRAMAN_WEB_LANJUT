from .factories import create_device, create_user

URL = "/api/v1/users"
VALID = {"username": "Andi", "email": "Andi@Example.com", "password": "Password123"}


def test_create_user_success_hides_password(client):
    response = client.post(URL, json=VALID)
    assert response.status_code == 201
    data = response.get_json()["data"]
    assert response.headers["Location"] == f"{URL}/{data['id']}"
    assert data["username"] == "andi"  # dinormalisasi ke huruf kecil
    assert data["email"] == "andi@example.com"
    assert data["role"] == "operator"
    assert "password" not in data and "password_hash" not in data


def test_create_user_validation_error(client):
    response = client.post(URL, json={**VALID, "password": "short", "role": "root"})
    assert response.status_code == 422
    error = response.get_json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert "password" in error["details"] and "role" in error["details"]


def test_password_needs_letter_and_digit(client):
    response = client.post(URL, json={**VALID, "password": "onlyletters"})
    assert response.status_code == 422


def test_create_user_duplicate_returns_409(client):
    client.post(URL, json=VALID)
    same_username = client.post(URL, json={**VALID, "email": "lain@example.com"})
    same_email = client.post(URL, json={**VALID, "username": "lain"})
    assert same_username.status_code == 409
    assert same_email.status_code == 409
    assert same_username.get_json()["error"]["code"] == "CONFLICT"


def test_list_users_supports_pagination_filter_and_search(client):
    create_user(username="admin1", role="admin")
    for i in range(4):
        create_user(username=f"operator{i}", email=f"op{i}@example.com")

    page = client.get(f"{URL}?per_page=2&page=2&sort=username").get_json()
    assert page["meta"] == {"page": 2, "per_page": 2, "total": 5, "pages": 3}
    assert [u["username"] for u in page["data"]] == ["operator1", "operator2"]

    admins = client.get(f"{URL}?role=admin").get_json()
    assert admins["meta"]["total"] == 1

    found = client.get(f"{URL}?q=OPERATOR3").get_json()
    assert [u["username"] for u in found["data"]] == ["operator3"]


def test_get_user_not_found(client):
    response = client.get(f"{URL}/999")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "NOT_FOUND"


def test_delete_user_blocked_while_owning_devices(client):
    device = create_device()
    blocked = client.delete(f"{URL}/{device.owner_id}")
    assert blocked.status_code == 409

    free_user = create_user()
    assert client.delete(f"{URL}/{free_user.id}").status_code == 204
    assert client.get(f"{URL}/{free_user.id}").status_code == 404
