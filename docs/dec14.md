# December 14 — Lineage Fixes

- Added lineage API under `/api/models/{model_id}/lineage` by including `bs/src/lineage/routes.py` in the FastAPI app.
- Kept lineage data model and helpers in `bs/src/lineage/` (`models.py`, `graph.py`, `parser.py`).
- Ensured DB init and router registration are resilient so lineage routes always load.
- Set up a fresh Python venv, installed deps, and adjusted `pytest.ini` to remove missing coverage plugin.
- Verified lineage tests in test/test_lineage.py pass locally.

## Minimal Usage
- Reset DB: `POST /api/reset`
- Query lineage: `GET /api/models/{model_id}/lineage`

This doc is intentionally concise to match the latest state.