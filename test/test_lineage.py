from fastapi.testclient import TestClient
from bs.src.app import app

from bs.src import models_db
from bs.src.lineage.models import upsert_edges


client = TestClient(app)


def setup_module(module):
    models_db.reset_db()
    models_db.init_db()


def test_basic_lineage_traversal():
    # create simple chain: C -> B -> A (A has parent B; B has parent C)
    db = models_db.SessionLocal()
    upsert_edges(db, "A", [{"parent_id": "B"}])
    upsert_edges(db, "B", [{"parent_id": "C"}])

    r = client.get("/api/models/A/lineage")
    assert r.status_code == 200, r.text
    j = r.json()
    assert j.get("model_id") == "A"
    ancestors = j.get("ancestors")
    # should include B (distance 1) and C (distance 2)
    ids = {a["model_id"]: a for a in ancestors}
    assert "B" in ids
    assert ids["B"]["distance"] == 1
    assert "C" in ids
    assert ids["C"]["distance"] == 2

    db.close()
