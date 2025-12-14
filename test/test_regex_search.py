import json
from fastapi.testclient import TestClient
from bs.src.app import app, store

def setup_module(module):
    # Ensure clean state
    store.clear_all()
    # Seed a couple of artifacts
    store.put_artifact({"id": None, "name": "alpha-model", "type": "model", "url": "http://example.com/a"})
    store.put_artifact({"id": None, "name": "beta-dataset", "type": "dataset", "url": "http://example.com/b"})

client = TestClient(app)

def test_regex_matches_alpha():
    resp = client.post("/artifact/byRegEx", data=json.dumps({"regex": "alpha"}))
    assert resp.status_code == 200
    names = [x["name"] for x in resp.json()]
    assert "alpha-model" in names

def test_regex_no_matches_returns_404():
    resp = client.post("/artifact/byRegEx", data=json.dumps({"regex": "nomatch"}))
    assert resp.status_code == 404

def test_bad_input_returns_400():
    resp = client.post("/artifact/byRegEx", data="not-json")
    assert resp.status_code == 400

def test_forbidden_nested_quantifiers_returns_400():
    # pattern like (.+)+ should be blocked
    resp = client.post("/artifact/byRegEx", data=json.dumps({"regex": "(.+)+"}))
    assert resp.status_code == 400

def test_long_regex_returns_400():
    long_pattern = "a" * 600
    resp = client.post("/artifact/byRegEx", data=json.dumps({"regex": long_pattern}))
    assert resp.status_code == 400
