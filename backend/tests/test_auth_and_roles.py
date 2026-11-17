import pytest

def test_login_success(client, test_users):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "test_admin@stocksense.dev", "password": "AdminPass123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == "test_admin@stocksense.dev"
    assert data["user"]["role"] == "ADMIN"

def test_login_invalid_password(client):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "test_admin@stocksense.dev", "password": "WrongPassword!"},
    )
    assert resp.status_code == 401

def test_admin_user_management_role_restriction(client, auth_headers):
    # Admin can list users
    res_admin = client.get("/api/v1/users", headers=auth_headers["admin"])
    assert res_admin.status_code == 200

    # Manager cannot list users (403 Forbidden)
    res_manager = client.get("/api/v1/users", headers=auth_headers["manager"])
    assert res_manager.status_code == 403

    # Staff cannot list users (403 Forbidden)
    res_staff = client.get("/api/v1/users", headers=auth_headers["staff"])
    assert res_staff.status_code == 403

def test_staff_cannot_create_stock_adjustment(client, auth_headers, test_setup_catalog):
    prod = test_setup_catalog["product"]
    wh = test_setup_catalog["warehouse"]

    # Staff role should be forbidden from manual stock adjustments
    res = client.post(
        "/api/v1/inventory/adjustments",
        headers=auth_headers["staff"],
        json={"product_id": prod.id, "warehouse_id": wh.id, "quantity_delta": 5, "reason": "Test adjustment"},
    )
    assert res.status_code == 403

def test_manager_can_create_stock_adjustment(client, auth_headers, test_setup_catalog):
    prod = test_setup_catalog["product"]
    wh = test_setup_catalog["warehouse"]

    res = client.post(
        "/api/v1/inventory/adjustments",
        headers=auth_headers["manager"],
        json={"product_id": prod.id, "warehouse_id": wh.id, "quantity_delta": 5, "reason": "Physical count surplus"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["quantity_delta"] == 5
    assert data["balance_after"] == 55
