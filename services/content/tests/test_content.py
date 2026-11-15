import pytest

from .conftest import DELETED

BASE = {"title": "Test Movie", "description": "A test", "genre": "Drama", "language": "English", "release_year": 2020, "duration_minutes": 100, "category": "movie"}


def make(client, admin_h, **over):
    r = client.post("/content", headers=admin_h, json={**BASE, **over})
    assert r.status_code == 201, r.text
    return r.json()


def test_admin_crud_lifecycle(client, admin_h, user_h):
    c = make(client, admin_h)
    cid = c["id"]
    assert client.get(f"/content/{cid}", headers=user_h).json()["title"] == "Test Movie"
    assert client.put(f"/content/{cid}", headers=admin_h, json={**BASE, "title": "Renamed"}).json()["title"] == "Renamed"
    assert client.patch(f"/content/{cid}", headers=admin_h, json={"genre": "Action"}).json()["genre"] == "Action"
    assert client.delete(f"/content/{cid}", headers=admin_h).status_code == 204
    assert DELETED == [cid]
    assert client.get(f"/content/{cid}", headers=user_h).status_code == 404
    assert client.delete(f"/content/{cid}", headers=admin_h).status_code == 404


def test_rbac(client, admin_h, user_h):
    assert client.post("/content", headers=user_h, json=BASE).status_code == 403
    assert client.post("/content", json=BASE).status_code == 401
    c = make(client, admin_h)
    assert client.delete(f"/content/{c['id']}", headers=user_h).status_code == 403
    assert client.get("/content/admin/stats", headers=user_h).status_code == 403
    assert client.get("/content").status_code == 401


@pytest.mark.parametrize("bad", [{"title": ""}, {"release_year": 1500}, {"duration_minutes": 0}, {"category": "podcast"}, {"description": "   "}])
def test_validation(client, admin_h, bad):
    assert client.post("/content", headers=admin_h, json={**BASE, **bad}).status_code == 422


def test_search_filter_sort_pagination(client, admin_h, user_h):
    make(client, admin_h, title="Alpha Quest", genre="Action", language="Hindi", category="movie", release_year=2019)
    make(client, admin_h, title="Beta Show", genre="Drama", language="English", category="tv_show", release_year=2022)
    make(client, admin_h, title="Gamma 100%", genre="Drama", language="Hindi", category="web_series", release_year=2021, is_featured=True)
    get = lambda qs: client.get(f"/content?{qs}", headers=user_h).json()  # noqa: E731
    assert get("")["total"] == 3
    assert [i["title"] for i in get("q=alpha")["items"]] == ["Alpha Quest"]
    assert get("q=100%25")["total"] == 1  # LIKE wildcards are escaped
    assert get("q=%25")["total"] == 1
    assert get("genre=Drama")["total"] == 2
    assert get("language=Hindi&category=web_series")["total"] == 1
    assert get("featured=true")["items"][0]["title"] == "Gamma 100%"
    assert [i["title"] for i in get("sort=title")["items"]] == ["Alpha Quest", "Beta Show", "Gamma 100%"]
    assert [i["release_year"] for i in get("sort=year")["items"]] == [2022, 2021, 2019]
    p = get("page=2&page_size=2")
    assert p["total"] == 3 and p["pages"] == 2 and len(p["items"]) == 1
    ids = ",".join(str(i["id"]) for i in get("")["items"][:2])
    assert get(f"ids={ids}")["total"] == 2
    assert client.get("/content?ids=a,b", headers=user_h).status_code == 400
    assert client.get("/content?category=bogus", headers=user_h).status_code == 422


def test_facets_and_stats(client, admin_h, user_h):
    make(client, admin_h, genre="Action", language="Tamil")
    make(client, admin_h, genre="Drama", language="Tamil", category="web_series", is_featured=True)
    f = client.get("/content/facets", headers=user_h).json()
    assert f["genres"] == ["Action", "Drama"] and f["languages"] == ["Tamil"] and set(f["categories"]) == {"movie", "web_series"}
    s = client.get("/content/admin/stats", headers=admin_h).json()
    assert s["total"] == 2 and s["featured"] == 1 and s["by_language"] == {"Tamil": 2} and s["added_last_7_days"] == 2
    assert client.get("/ready").status_code == 200
