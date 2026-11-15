def test_progress_upsert_and_resume(client, h1):
    r = client.put("/history/9", headers=h1, json={"position_seconds": 120.5, "duration_seconds": 3600})
    assert r.status_code == 200 and r.json()["completed"] is False
    client.put("/history/9", headers=h1, json={"position_seconds": 300, "duration_seconds": 3600})
    got = client.get("/history/9", headers=h1).json()
    assert got["position_seconds"] == 300
    assert client.get("/history", headers=h1).json()["total"] == 1


def test_completion_and_in_progress_filter(client, h1):
    client.put("/history/1", headers=h1, json={"position_seconds": 3500, "duration_seconds": 3600})
    client.put("/history/2", headers=h1, json={"position_seconds": 100, "duration_seconds": 3600})
    assert client.get("/history/1", headers=h1).json()["completed"] is True
    ids = [i["content_id"] for i in client.get("/history?in_progress=true", headers=h1).json()["items"]]
    assert ids == [2]


def test_position_clamped_and_validation(client, h1):
    r = client.put("/history/3", headers=h1, json={"position_seconds": 9999, "duration_seconds": 100})
    assert r.json()["position_seconds"] == 100
    assert client.put("/history/3", headers=h1, json={"position_seconds": -1, "duration_seconds": 100}).status_code == 422
    assert client.get("/history/404", headers=h1).status_code == 404


def test_isolation_delete_clear(client, h1, h2):
    client.put("/history/1", headers=h1, json={"position_seconds": 10, "duration_seconds": 100})
    client.put("/history/2", headers=h1, json={"position_seconds": 10, "duration_seconds": 100})
    assert client.get("/history", headers=h2).json()["total"] == 0
    assert client.delete("/history/1", headers=h1).status_code == 204
    assert client.get("/history", headers=h1).json()["total"] == 1
    assert client.delete("/history", headers=h1).status_code == 204
    assert client.get("/history", headers=h1).json()["total"] == 0
    assert client.get("/history").status_code == 401
