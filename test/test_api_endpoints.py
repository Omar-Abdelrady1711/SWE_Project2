import os, sys
sys.path.append(os.path.abspath("bs/src"))  # ensures bs/src is importable
from fastapi.testclient import TestClient
from app import app  # or from bs.src.app import app if that's your module path
client = TestClient(app)  


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    j = r.json()
    assert j["status"] == "ok"
    assert j["phase"] == 2

def test_all_resets_exist_and_clear_store():
    # hit all four reset endpoints to cover them
    for path in ["/api/reset", "/api/system/reset"]:
        assert client.post(path).status_code == 200
        assert client.get(path).status_code == 200
    # after reset, list is empty
    r = client.get("/api/artifacts")
    assert r.status_code == 200
    assert r.json() == {"artifacts": []}

def test_ingest_valid_and_listing_and_get_by_id_and_name():
    # valid ingest
    r = client.post("/api/ingest", json={"type": "model", "name": "m1", "meta": {"a": 1}})
    assert r.status_code == 201
    new_id = r.json()["id"]

    # list shows it
    r = client.get("/api/artifacts")
    body = r.json()
    assert len(body["artifacts"]) == 1
    assert body["artifacts"][0]["id"] == new_id

    # get by id
    r = client.get(f"/api/artifacts/{new_id}")
    assert r.status_code == 200
    assert r.json()["name"] == "m1"

    # get by name
    r = client.get("/api/artifacts/by_name/m1")
    assert r.status_code == 200
    assert r.json()["id"] == new_id

def test_ingest_invalid_type_and_missing_name():
    # bad type
    r = client.post("/api/ingest", json={"type": "oops", "name": "x"})
    assert r.status_code == 400
    # missing name
    r = client.post("/api/ingest", json={"type": "model"})
    assert r.status_code == 400

def test_query_filters_and_regex_and_not_found_routes():
    # seed three
    client.post("/api/reset")
    client.post("/api/ingest", json={"type": "model", "name": "alpha"})
    client.post("/api/ingest", json={"type": "dataset", "name": "beta"})
    client.post("/api/ingest", json={"type": "code", "name": "alphonse"})

    # filter by type
    r = client.get("/api/query", params={"type": "dataset"})
    assert [a["name"] for a in r.json()["artifacts"]] == ["beta"]

    # exact name
    r = client.get("/api/query", params={"name": "alpha"})
    assert [a["name"] for a in r.json()["artifacts"]] == ["alpha"]

    # regex branch
    r = client.get("/api/query", params={"name": r"^alph", "regex": True})
    names = [a["name"] for a in r.json()["artifacts"]]
    assert set(names) == {"alpha", "alphonse"}

    # not found by id
    assert client.get("/api/artifacts/9999").status_code == 404
    # not found by name
    assert client.get("/api/artifacts/by_name/zzz").status_code == 404

def test_api_root_and_root_redirect():
    r = client.get("/api/")
    assert r.status_code == 200
    assert r.json()["message"] == "Backend running"

    r = client.get("/")              # follows redirect
    assert r.status_code == 200      # final page OK
    assert r.history                 # there was a redirect
    assert r.history[0].status_code in (307, 308)
    assert r.history[0].headers["location"].endswith("/api")


