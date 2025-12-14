# December 14 Updates

## Summary
- Switched local repo to `main` and pulled latest from `origin/main` (fast-forward).
- Reviewed backend `bs/src/app.py` to identify quick rubric-aligned endpoints already present.
- Confirmed reset endpoints exist and are functional: `/api/reset`, `/api/system/reset`, and `/reset` (GET/POST), all invoking `reset_db()` and `store.clear_all()`.
- Confirmed regex search endpoint exists: `POST /artifact/byRegEx` with robust 400 handling and 404 on no matches.
- Confirmed baseline artifact CRUD and rating endpoints exist for autograder coverage:
  - Ingest: `POST /artifact/{artifact_type}` (creates and rates `model` artifacts).
  - Get All: `GET /artifact`.
  - Get by Name: `GET /artifact/byName/{name}`.
  - Get by Type+ID: `GET /artifact/{artifact_type}/{id}` and `GET /artifacts/{artifact_type}/{id}`.
  - Delete: `DELETE /artifact/{artifact_type}/{id}`.
  - Rate: `GET /artifact/model/{id}/rate` returns `ModelRatingOut`.
- Verified storage abstraction is in place:
  - Local SQLite via `LocalStore` with `init_db/reset_db` (Phase 1 DB) and ratings in memory.
  - DynamoDB via `DynamoStore` (lazy import), auto-ID allocation, and `reset_all`.

## New Changes (Dec 14)
- Added safe-regex guard to `POST /artifact/byRegEx` in `bs/src/app.py`:
  - Limits pattern length to 512 chars.
  - Blocks nested quantifiers like `(.*)+`, `(.+)+`, `(.*)*`, `(.+)*`.
  - Limits capture groups to 64.
  - Continues to return 400 for malformed regex and 404 for no matches.
- Added unit tests `test/test_regex_search.py` covering:
  - Successful match for a simple pattern.
  - 404 when no artifacts match.
  - 400 for non-JSON body.
  - 400 for forbidden nested quantifiers.
  - 400 for overly long regex.

Note: Running the new tests requires FastAPI test dependencies. If `fastapi` is missing, install with:

```powershell
pip install -r requirements.txt
```

## Rubric Mapping (Quick Wins Already Available)
- Reset to Default State: Implemented via `/api/reset`, `/api/system/reset`, and `/reset`.
- Regex Search: Implemented via `POST /artifact/byRegEx`.
- Get Artifact: Implemented via `GET /artifact` and by type+id endpoints.
- Upload/Ingest Artifact: Implemented via `POST /artifact/{artifact_type}`.
- Delete Artifact: Implemented via `DELETE /artifact/{artifact_type}/{id}`.
- Rate Artifact: Implemented via `GET /artifact/model/{id}/rate`.

## Suggested Next Quick Steps
- Add Cost endpoint: `GET /artifact/{id}/cost` aggregating size/ingest metadata recursively.
- Lineage endpoint: `GET /artifacts/{id}/lineage` returning DAG (dependencies). Utilize `bs/src/lineage` and store relations.
- Frontend pages for Lineage + Search; run Lighthouse and store ADA results in `docs/lighthouse.html`.
- Extend tests: create focused tests for reset, regex, lineage, and cost under `test/`.

## Verification Commands
Run basic checks:

```powershell
pytest -q
curl -X POST http://localhost:8000/api/reset
```

If you want, I can implement the Cost endpoint and its tests next.