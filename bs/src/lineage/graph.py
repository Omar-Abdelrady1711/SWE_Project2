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
    """Detect a cycle reachable from model_id using an iterative DFS with on-stack tracking."""
    onstack: Set[str] = set()
    stack: List[tuple[str, int]] = [(model_id, 0)]  # node, next-parent-index
    parents_cache: Dict[str, List[Dict]] = {}

    while stack:
        node, idx = stack[-1]
        if node not in parents_cache:
            parents_cache[node] = get_parents(session, node)
            onstack.add(node)

        parents = parents_cache[node]
        if idx >= len(parents):
            # done exploring this node
            onstack.discard(node)
            stack.pop()
            continue

        # explore next parent
        pid = parents[idx].get("parent_id")
        stack[-1] = (node, idx + 1)

        if pid in onstack:
            return True
        if pid is not None:
            stack.append((pid, 0))

    return False
