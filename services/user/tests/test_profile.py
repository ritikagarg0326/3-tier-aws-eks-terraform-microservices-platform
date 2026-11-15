from .conftest import headers_for


def test_profile_lazy_create_and_update(client, h1):
    me = client.get("/users/me", headers=h1).json()
    assert me["display_name"] == "viewer" and me["user_id"] == 1 and me["email"] == "u1@example.com"
    upd = client.put("/users/me", headers=h1, json={"display_name": "  Ritu ", "bio": "hi", "preferred_language": "Hindi", "avatar_color": "#ff0000"})
    assert upd.status_code == 200 and upd.json()["display_name"] == "Ritu"
    assert client.get("/users/me", headers=h1).json()["preferred_language"] == "Hindi"


def test_profiles_are_isolated(client, h1, h2):
    client.put("/users/me", headers=h1, json={"display_name": "A"})
    assert client.get("/users/me", headers=h2).json()["display_name"] == "other"


def test_validation_and_auth(client, h1):
    assert client.put("/users/me", headers=h1, json={"display_name": "  "}).status_code == 422
    assert client.put("/users/me", headers=h1, json={"display_name": "x", "avatar_color": "red"}).status_code == 422
    assert client.get("/users/me").status_code == 401


def test_delete_profile_and_health(client, h1):
    client.get("/users/me", headers=h1)
    assert client.delete("/users/me", headers=h1).status_code == 204
    assert client.get("/ready").status_code == 200
