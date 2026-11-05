from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_create_and_get(client: TestClient) -> None:
    r = client.post("/notes", json={"title": "Hi", "tags": [" B ", "a", "b"]})
    assert r.status_code == 201, r.text
    note = r.json()
    assert note["tags"] == ["a", "b"]          # validator normalised
    assert client.get(f"/notes/{note['id']}").json()["title"] == "Hi"


def test_validation_error(client: TestClient) -> None:
    r = client.post("/notes", json={"title": "", "nope": 1})
    assert r.status_code == 422
    fields = {e["loc"][-1] for e in r.json()["detail"]}
    assert {"title", "nope"} <= fields


def test_404(client: TestClient) -> None:
    r = client.get("/notes/999")
    assert r.status_code == 404
    assert r.json()["id"] == 999


def test_patch_partial(client: TestClient) -> None:
    nid = client.post("/notes", json={"title": "t", "body": "b"}).json()["id"]
    r = client.patch(f"/notes/{nid}", json={"body": "changed"})
    assert r.json()["title"] == "t" and r.json()["body"] == "changed"


def test_list_pagination_and_filter(client: TestClient) -> None:
    for i in range(5):
        client.post("/notes", json={"title": str(i), "tags": ["even" if i % 2 == 0 else "odd"]})
    page = client.get("/notes", params={"limit": 2, "offset": 1, "tag": "even"}).json()
    assert page["total"] == 3 and len(page["items"]) == 2
    assert client.get("/notes", params={"limit": 999}).status_code == 422


def test_delete(client: TestClient) -> None:
    nid = client.post("/notes", json={"title": "x"}).json()["id"]
    assert client.delete(f"/notes/{nid}").status_code == 204
    assert client.get(f"/notes/{nid}").status_code == 404
