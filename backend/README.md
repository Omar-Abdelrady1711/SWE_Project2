This backend is a minimal FastAPI CRUD service intended as an MVP for the SWE project.

Quick start (PowerShell):

```
python -m venv .venv; .\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

DB: SQLite file `backend.db` created in the project root when the app starts.
