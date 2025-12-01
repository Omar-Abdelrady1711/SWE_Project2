"""Parser utilities for extracting lineage from config.json-like metadata."""
from typing import Any, Dict, List


def extract_parents_from_config(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Given a config dict, return list of parent dicts with keys: parent_id, relation, metadata.

    Handles several common field names used in various projects.
    """
    parents = []

    # canonical single-parent keys
    single_keys = ["parent", "parent_id", "parent_model", "derived_from"]
    for k in single_keys:
        if k in config and config[k]:
            parents.append({"parent_id": str(config[k]), "relation": "derived", "metadata": None})
            # prefer single-parent if present
            return parents

    # plural parents
    multi_keys = ["parents", "parent_models", "derived_from_list", "sources"]
    for k in multi_keys:
        if k in config and config[k]:
            vals = config[k]
            if isinstance(vals, str):
                vals = [vals]
            for v in vals:
                parents.append({"parent_id": str(v), "relation": "derived", "metadata": None})
            return parents

    # fallback: check nested metadata path 'training.parent'
    t = config.get("training") or {}
    p = t.get("parent")
    if p:
        parents.append({"parent_id": str(p), "relation": "derived", "metadata": None})

    return parents
