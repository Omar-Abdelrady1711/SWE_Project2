from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, Dict, List, Set
from bs.src.models_db import get_session
from bs.src.lineage.graph import get_ancestors, detect_cycle
from bs.src.lineage.models import get_parents

router = APIRouter(prefix="/models", tags=["lineage"])


@router.get("/{model_id}/lineage")
def api_get_lineage(model_id: str, depth: Optional[int] = None, format: str = "list", db=Depends(get_session)):
    # simple validation
    if depth is not None and depth <= 0:
        raise HTTPException(status_code=400, detail="depth must be > 0")

    ancestors = get_ancestors(db, model_id, depth)
    cycle = detect_cycle(db, model_id)

    if format == "graph":
        # Build graph representation: nodes + relationships
        nodes: List[Dict] = []
        relationships: List[Dict] = []
        seen: Set[str] = set()

        # include the queried node
        nodes.append({"id": str(model_id)})
        seen.add(str(model_id))

        # include ancestor nodes
        for a in ancestors:
            aid = str(a.get("model_id"))
            if aid not in seen:
                nodes.append({"id": aid})
                seen.add(aid)

        # create relationships: for each node, add edges to its direct parents
        to_process = [str(model_id)] + [str(a.get("model_id")) for a in ancestors]
        processed: Set[str] = set()
        for child in to_process:
            if child in processed:
                continue
            parents = get_parents(db, child)
            for p in parents:
                pid = str(p.get("parent_id"))
                relationships.append({
                    "from": child,
                    "to": pid,
                    "relation": p.get("relation") or "derived",
                })
            processed.add(child)

        return {
            "model_id": str(model_id),
            "nodes": nodes,
            "relationships": relationships,
            "cycle": cycle,
        }

    # default/list format
    return {"model_id": model_id, "ancestors": ancestors, "cycle": cycle}
