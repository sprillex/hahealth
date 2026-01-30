import pytest
from app import models, auth
from fastapi.testclient import TestClient

def test_api_key_management(client: TestClient, session):
    # 0. Setup User
    user = models.User(
        name="apikey_mgr_user",
        password_hash=auth.get_password_hash("password"),
        weight_kg=70.0,
        height_cm=175.0
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    # 1. Login
    login_res = client.post("/auth/token", data={"username": "apikey_mgr_user", "password": "password"})
    assert login_res.status_code == 200, login_res.text
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. List Keys (Should be empty)
    res = client.get("/api/v1/users/me/keys", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) == 0

    # 3. Create Key
    create_payload = {"name": "My New Key"}
    res = client.post("/api/v1/users/me/keys", json=create_payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "My New Key"
    assert "api_key" in data
    raw_key = data["api_key"]
    key_id = data["key_id"]

    # 4. List Keys (Should have 1)
    res = client.get("/api/v1/users/me/keys", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["name"] == "My New Key"
    # Ensure raw key is NOT returned in list
    assert "api_key" not in res.json()[0]

    # 5. Use the new key to access an endpoint (e.g. /users/me)
    key_headers = {"Authorization": f"Bearer {raw_key}"}
    res = client.get("/api/v1/users/me", headers=key_headers)
    assert res.status_code == 200
    assert res.json()["name"] == "apikey_mgr_user"

    # 6. Revoke Key
    res = client.delete(f"/api/v1/users/me/keys/{key_id}", headers=headers)
    assert res.status_code == 200

    # 7. List Keys (Should be empty, as we filter by is_active=True)
    res = client.get("/api/v1/users/me/keys", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) == 0

    # 8. Try to use revoked key (Should fail)
    res = client.get("/api/v1/users/me", headers=key_headers)
    assert res.status_code == 401
