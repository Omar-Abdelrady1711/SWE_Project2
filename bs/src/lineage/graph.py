from typing import Dict, List, Set
from bs.src.lineage.models import get_parents


def get_ancestors(session, model_id: str, depth: int | None = None) -> List[Dict]:
    """Return list of ancestor nodes with distance (1 = direct parent).

    Depth=None means traverse until no more parents or until cycle detected.
    """
    ancestors = []
    visited: Set[str] = set()
    frontier = [(model_id, 0)]

    while frontier:
        current, dist = frontier.pop(0)
        if depth is not None and dist >= depth:
            continue
        parents = get_parents(session, current)
        for p in parents:
            pid = p.get("parent_id")
            if pid in visited:
                # skip cycles
                continue
            visited.add(pid)
            ancestors.append({"model_id": pid, "distance": dist + 1, "metadata": p.get("metadata")})
            frontier.append((pid, dist + 1))

    return ancestors


def detect_cycle(session, model_id: str) -> bool:
    # simple visited traversal to detect back-edge
    visited = set()
    stack = [model_id]
    while stack:
        current = stack.pop()
        if current in visited:
            return True
        visited.add(current)
        parents = get_parents(session, current)
        for p in parents:
            pid = p.get("parent_id")
            if pid not in visited:
                stack.append(pid)
    return False
