**Nov 16th CRUD Scaffold**

**Summary**: Added a minimal FastAPI CRUD backend scaffold under `backend/` to serve as an MVP. The scaffold includes SQLModel-based ORM models, a CRUD router, DB initialization, a `requirements.txt`, and a `Dockerfile`.

**Files added**:
- `backend/README.md` — quick startup instructions.
- `backend/requirements.txt` — Python dependencies (fastapi, uvicorn, sqlmodel, paho-mqtt, alembic, python-dotenv).
- `backend/Dockerfile` — simple image for running the app.
- `backend/app/__init__.py`
- `backend/app/db.py` — SQLModel engine and `get_session` dependency. Defaults to `sqlite:///backend.db`.
- `backend/app/models.py` — SQLModel models: `Device`, `FishProfile`, `SensorReading`, `Schedule`, `Config`.
- `backend/app/crud.py` — `APIRouter` providing basic CRUD endpoints for devices, readings, and fish profiles.
- `backend/app/main.py` — FastAPI app entrypoint, initializes DB on startup and can optionally start the MQTT bridge.

**How to run (local)**

1. Create a venv and install dependencies:

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
uvicorn backend.app.main:app --reload --port 8000
```

2. Open API docs at `http://127.0.0.1:8000/docs`.


**Notes & Next steps**
- Authentication: the scaffold doesn't include auth. Add API key or OAuth2 for production write endpoints.
- Migrations: `alembic` is added to `requirements.txt`. If you prefer DB migrations, add `alembic` config and env.
- Extend `mqtt_bridge.py` to insert sensor readings into the DB and to expose publish helpers to the API.
- Tests: add unit tests for each endpoint and integration tests for DB persistence and MQTT behavior.
- Docker: the `Dockerfile` is minimal; consider adding multi-stage build and non-root user.
