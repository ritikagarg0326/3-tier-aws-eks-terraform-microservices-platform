from .conftest import register


def test_register_login_me(client):
    r = register(client)
    assert r.status_code == 201
    body = r.json()
    assert body["user"]["role"] == "user" and "password" not in str(body)
    assert client.post("/auth/login", json={"email": "VIEWER@example.com", "password": "Passw0rd!x"}).status_code == 200
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200 and me.json()["email"] == "viewer@example.com"


def test_duplicate_and_validation(client):
    register(client)
    assert register(client).json()["error"]["code"] == "email_taken"
    assert register(client, email="b@example.com").json()["error"]["code"] == "username_taken"
    weak = register(client, email="c@example.com", username="c1", password="short")
    assert weak.status_code == 422 and weak.json()["error"]["code"] == "validation_error"
    assert register(client, email="not-an-email", username="d1").status_code == 422


def test_wrong_password_and_unknown_user(client):
    register(client)
    assert client.post("/auth/login", json={"email": "viewer@example.com", "password": "nope"}).status_code == 401
    assert client.post("/auth/login", json={"email": "ghost@example.com", "password": "nope"}).status_code == 401


def test_me_requires_token(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_refresh_rotation_and_reuse_detection(client, user_tokens):
    first = user_tokens["refresh_token"]
    second = client.post("/auth/refresh", json={"refresh_token": first})
    assert second.status_code == 200
    reuse = client.post("/auth/refresh", json={"refresh_token": first})
    assert reuse.status_code == 401 and reuse.json()["error"]["code"] == "token_revoked"
    # family revoked -> the rotated token no longer works either
    assert client.post("/auth/refresh", json={"refresh_token": second.json()["refresh_token"]}).status_code == 401


def test_access_token_cannot_be_used_as_refresh(client, user_tokens):
    assert client.post("/auth/refresh", json={"refresh_token": user_tokens["access_token"]}).status_code == 401


def test_logout_revokes(client, user_tokens):
    rt = user_tokens["refresh_token"]
    assert client.post("/auth/logout", json={"refresh_token": rt}).status_code == 204
    assert client.post("/auth/refresh", json={"refresh_token": rt}).status_code == 401


def test_change_password(client, user_tokens):
    h = {"Authorization": f"Bearer {user_tokens['access_token']}"}
    assert client.post("/auth/change-password", headers=h, json={"current_password": "bad", "new_password": "NewPass123"}).status_code == 401
    assert client.post("/auth/change-password", headers=h, json={"current_password": "Passw0rd!x", "new_password": "NewPass123"}).status_code == 204
    assert client.post("/auth/login", json={"email": "viewer@example.com", "password": "NewPass123"}).status_code == 200


def test_admin_rbac(client, user_tokens, admin_headers):
    user_h = {"Authorization": f"Bearer {user_tokens['access_token']}"}
    assert client.get("/auth/admin/users", headers=user_h).status_code == 403
    assert client.get("/auth/admin/users").status_code == 401
    listing = client.get("/auth/admin/users", headers=admin_headers).json()
    assert listing["total"] == 2
    uid = user_tokens["user"]["id"]
    promoted = client.patch(f"/auth/admin/users/{uid}", headers=admin_headers, json={"role": "admin"})
    assert promoted.status_code == 200 and promoted.json()["role"] == "admin"
    assert client.patch(f"/auth/admin/users/{uid}", headers=admin_headers, json={"role": "root"}).status_code == 422


def test_admin_cannot_self_modify_and_deactivation_blocks_login(client, user_tokens, admin_headers):
    me = client.get("/auth/me", headers=admin_headers).json()
    assert client.patch(f"/auth/admin/users/{me['id']}", headers=admin_headers, json={"is_active": False}).status_code == 403
    assert client.delete(f"/auth/admin/users/{me['id']}", headers=admin_headers).status_code == 403
    uid = user_tokens["user"]["id"]
    client.patch(f"/auth/admin/users/{uid}", headers=admin_headers, json={"is_active": False})
    assert client.post("/auth/login", json={"email": "viewer@example.com", "password": "Passw0rd!x"}).status_code == 401
    assert client.post("/auth/refresh", json={"refresh_token": user_tokens["refresh_token"]}).status_code == 401
    assert client.delete(f"/auth/admin/users/{uid}", headers=admin_headers).status_code == 204
    assert client.delete(f"/auth/admin/users/{uid}", headers=admin_headers).status_code == 404


def test_stats_and_health(client, admin_headers):
    s = client.get("/auth/admin/stats", headers=admin_headers).json()
    assert s["total_users"] == 1 and s["admins"] == 1
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/ready").json()["checks"]["database"] == "ok"
