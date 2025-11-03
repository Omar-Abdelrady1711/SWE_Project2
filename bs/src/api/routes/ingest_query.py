from fastapi import APIRouter

router = APIRouter(prefix="/ingest", tags=["ingest"])

@router.get("/health")
def ingest_health():
    return {"status": "ok"}
