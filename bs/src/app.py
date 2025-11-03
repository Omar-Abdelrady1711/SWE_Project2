from fastapi import FastAPI, status
from src.api.routes.artifacts import router as artifacts_router
from src.api.routes.ingest_query import router as ingest_query_router  # you added this file
from src.models_db import Base, engine

app = FastAPI(title="ECE461 Phase 2 API")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/reset", status_code=status.HTTP_204_NO_CONTENT)
def reset():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return

@app.get("/tracks")
def tracks():
    return [{"name": "access-control"}]

app.include_router(artifacts_router, prefix="")
app.include_router(ingest_query_router, prefix="")

