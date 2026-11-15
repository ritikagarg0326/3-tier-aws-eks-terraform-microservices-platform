def test_add_list_remove(client, h1):
    assert client.post("/watchlist", headers=h1, json={"content_id": 5}).status_code == 201
    assert client.post("/watchlist", headers=h1, json={"content_id": 5}).status_code == 200  # idempotent
    client.post("/watchlist", headers=h1, json={"content_id": 7})
    page = client.get("/watchlist", headers=h1).json()
    assert page["total"] == 2 and [i["content_id"] for i in page["items"]] == [7, 5]
    assert sorted(client.get("/watchlist/ids", headers=h1).json()) == [5, 7]
    assert client.get("/watchlist/5", headers=h1).json()["in_watchlist"] is True
    assert client.delete("/watchlist/5", headers=h1).status_code == 204
    assert client.delete("/watchlist/5", headers=h1).status_code == 204
    assert client.get("/watchlist/5", headers=h1).json()["in_watchlist"] is False


def test_isolation_between_users(client, h1, h2):
    client.post("/watchlist", headers=h1, json={"content_id": 1})
    assert client.get("/watchlist", headers=h2).json()["total"] == 0


def test_validation_auth_pagination(client, h1):
    assert client.post("/watchlist", headers=h1, json={"content_id": 0}).status_code == 422
    assert client.get("/watchlist").status_code == 401
    for i in range(1, 6):
        client.post("/watchlist", headers=h1, json={"content_id": i})
    p = client.get("/watchlist?page=2&page_size=2", headers=h1).json()
    assert p["pages"] == 3 and len(p["items"]) == 2
    assert client.get("/ready").status_code == 200
