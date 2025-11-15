from fastapi import APIRouter, HTTPException
from bs.src.acemcli.orchestrator import compute_all
from bs.src.acemcli.models import Category

router = APIRouter()

@router.post("/rating")
def rate_model(url: str):
    """
    Compute metrics for a single model URL using Phase 1 metrics engine.
    """
    try:
        results, errors = compute_all([(url, "MODEL")])

        if errors:
            raise HTTPException(status_code=400, detail=str(errors))

        return results[0]  # return the MetricResult for that one URL
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rating failed: {e}")
