from fastapi.testclient import TestClient
from bs.src.app import app
from bs.src.models_db import SessionLocal, reset_db, init_db
from bs.src.lineage.models import upsert_edges, get_parents
from bs.src.lineage.parser import extract_parents_from_config
from bs.src.lineage.graph import get_ancestors, detect_cycle
from bs.src.acemcli.metrics.tree_score import TreeScoreMetric


client = TestClient(app)


def setup_module(module):
    reset_db()
    init_db()


def test_parser_extracts_parents_from_config_variants():
    # single-parent keys
    cfg1 = {"parent_id": "http://repo/parent1"}
    parents1 = extract_parents_from_config(cfg1)
    assert len(parents1) == 1 and parents1[0]["parent_id"] == "http://repo/parent1"

    # multi-parent list
    cfg2 = {"parents": ["http://repo/pA", "http://repo/pB"]}
    parents2 = extract_parents_from_config(cfg2)
    assert {p["parent_id"] for p in parents2} == {"http://repo/pA", "http://repo/pB"}


def test_graph_ancestors_and_cycle_detection():
    db = SessionLocal()
    try:
        # modelA has parents p1 and p2; p1 has parent p3
        upsert_edges(db, "modelA", [
            {"parent_id": "p1"},
            {"parent_id": "p2"},
        ])
        upsert_edges(db, "p1", [
            {"parent_id": "p3"},
        ])

        anc = get_ancestors(db, "modelA")
        # Expect p1, p2 at distance 1; p3 at distance 2
        dmap = {a["model_id"]: a["distance"] for a in anc}
        assert dmap["p1"] == 1 and dmap["p2"] == 1 and dmap["p3"] == 2

        # Introduce a cycle: p3 -> modelA
        upsert_edges(db, "p3", [{"parent_id": "modelA"}])
        assert detect_cycle(db, "modelA") is True
    finally:
        db.close()


def test_lineage_api_returns_ancestors_list():
    db = SessionLocal()
    try:
        upsert_edges(db, "alpha", [{"parent_id": "beta"}, {"parent_id": "gamma"}])
    finally:
        db.close()

    r = client.get("/api/models/alpha/lineage")
    assert r.status_code == 200, r.text
    payload = r.json()
    mids = {a["model_id"] for a in payload.get("ancestors", [])}
    assert mids == {"beta", "gamma"}


def test_tree_score_metric_averages_parent_net_scores(monkeypatch):
    # Prepare lineage: target model with two parents (treated as URLs for scoring)
    db = SessionLocal()
    try:
        upsert_edges(db, "delta", [
            {"parent_id": "http://repo/p1"},
            {"parent_id": "http://repo/p2"},
        ])
    finally:
        db.close()

    # Monkeypatch orchestrator to return deterministic net scores for the parents
    from bs.src import acemcli
    from bs.src.acemcli import orchestrator as orch

    class _Res:
        def __init__(self, name, score):
            self.name = name
            self.category = "MODEL"
            self.net_score = score
            self.net_score_latency = 0

    def fake_compute_one(url, cat):
        if "p1" in url:
            return _Res(url, 0.6)
        if "p2" in url:
            return _Res(url, 0.8)
        return _Res(url, 0.0)

    monkeypatch.setattr(orch, "_compute_one", fake_compute_one)

    metric = TreeScoreMetric()
    res = metric.compute("http://repo/delta", "MODEL")
    assert abs(res.tree_score - ((0.6 + 0.8) / 2)) < 1e-6
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
