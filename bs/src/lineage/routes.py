from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from bs.src.models_db import get_session
from bs.src.lineage.graph import get_ancestors, detect_cycle

router = APIRouter(prefix="/models", tags=["lineage"])


@router.get("/{model_id}/lineage")
def api_get_lineage(model_id: str, depth: Optional[int] = None, format: str = "list", db=Depends(get_session)):
    # simple validation
    if depth is not None and depth <= 0:
        raise HTTPException(status_code=400, detail="depth must be > 0")

    ancestors = get_ancestors(db, model_id, depth)
    cycle = detect_cycle(db, model_id)
    if format == "tree":
        # convert flat ancestor list to nested tree is non-trivial; return list for now
        return {"model_id": model_id, "ancestors": ancestors, "cycle": cycle}
    return {"model_id": model_id, "ancestors": ancestors, "cycle": cycle}
