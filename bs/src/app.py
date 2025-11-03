from fastapi import FastAPI
from src.models_db import init_db
from src.api.routes.artifacts import router as artifacts_router

app = FastAPI()
init_db()  # create tables on startup

app.include_router(artifacts_router, prefix="/artifacts", tags=["artifacts"])

@app.get("/health")
def health():
    return {"status": "ok"}
