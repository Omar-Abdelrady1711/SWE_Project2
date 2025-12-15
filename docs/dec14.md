# December 14 Updates (Simplified)

## What Changed
- Implemented lineage support in backend:
  - Schemas added in `bs/src/schemas.py` (`LineageGraphOut`, `LineageUpdateIn`, `LineageEdge`).
  - In-memory lineage storage wired into `LocalStore` and `DynamoStore` in `bs/src/app.py`.
  - Endpoints:
    - `GET /artifact/{artifact_type}/{id}/lineage` returns ancestors and edges.
    - `POST /artifact/{artifact_type}/{id}/lineage` sets parents for an artifact.
- Kept existing reset, ingest, list, get-by-name, get-by-id, delete, and rating endpoints.

## How To Use
- Set parents:
  - POST body: `{ "parents": ["1", "2"] }`
- Fetch lineage:
  - GET response includes: `id`, `type`, `name`, `ancestors` (list of parent IDs), `edges` (parent→child pairs).

## Quick Commands
```powershell
# Reset
curl -X POST http://localhost:8000/api/reset

# Ingest examples
curl -X POST http://localhost:8000/artifact/model -H "Content-Type: application/json" -d "{\"url\":\"https://huggingface.co/user/modelA\"}"
curl -X POST http://localhost:8000/artifact/dataset -H "Content-Type: application/json" -d "{\"url\":\"https://huggingface.co/datasets/user/data1\"}"

# Set lineage (if model id=3, parent dataset id=2)
curl -X POST http://localhost:8000/artifact/model/3/lineage -H "Content-Type: application/json" -d "{\"parents\":[\"2\"]}"

# Get lineage
curl http://localhost:8000/artifact/model/3/lineage

# Run tests
pytest -q
```

