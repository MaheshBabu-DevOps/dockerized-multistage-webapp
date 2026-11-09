import pytest


def test_health_reports_dependencies(client):
    assert client.get("/api/health").json() == {"status": "ok", "database": "up", "cache": "up"}


def test_create_list_delete(client):
    created = client.post("/api/notes", json={"title": "First", "content": "hello"})
    assert created.status_code == 201
    note_id = created.json()["id"]
    assert [n["title"] for n in client.get("/api/notes").json()] == ["First"]
    assert client.delete(f"/api/notes/{note_id}").status_code == 204
    assert client.get("/api/notes").json() == []


def test_list_is_newest_first(client):
    for title in ("a", "b", "c"):
        client.post("/api/notes", json={"title": title})
    assert [n["title"] for n in client.get("/api/notes").json()] == ["c", "b", "a"]


def test_second_list_call_is_served_from_cache(client):
    client.post("/api/notes", json={"title": "cached"})
    assert client.get("/api/notes").headers["x-cache"] == "MISS"
    assert client.get("/api/notes").headers["x-cache"] == "HIT"


def test_write_invalidates_cache(client):
    client.get("/api/notes")
    client.get("/api/notes")  # now cached
    client.post("/api/notes", json={"title": "new"})
    response = client.get("/api/notes")
    assert response.headers["x-cache"] == "MISS"
    assert [n["title"] for n in response.json()] == ["new"]


def test_delete_invalidates_cache(client):
    note_id = client.post("/api/notes", json={"title": "temp"}).json()["id"]
    client.get("/api/notes")
    client.delete(f"/api/notes/{note_id}")
    assert client.get("/api/notes").json() == []


def test_delete_unknown_note_404(client):
    assert client.delete("/api/notes/999").status_code == 404


@pytest.mark.parametrize(
    "payload", [{"title": ""}, {"title": "x" * 101}, {"title": "ok", "content": "y" * 2001}, {}]
)
def test_validation_errors(client, payload):
    assert client.post("/api/notes", json=payload).status_code == 422


def test_api_keeps_working_when_redis_is_down(client_without_redis):
    c = client_without_redis
    assert c.post("/api/notes", json={"title": "still works"}).status_code == 201
    response = c.get("/api/notes")
    assert response.status_code == 200
    assert response.headers["x-cache"] == "MISS"
    assert response.json()[0]["title"] == "still works"
    assert c.get("/api/health").json()["cache"] == "down"
