from __future__ import annotations
import sys
import json
from dataclasses import asdict, is_dataclass
from typing import Iterable


def _to_serializable(obj):
    # asdict expects a dataclass *instance*. Some editors/type-checkers
    # warn because is_dataclass() can be True for dataclass *types* as well.
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    if isinstance(obj, dict):
        return obj
    return str(obj)


def write_ndjson(results: Iterable, file=None) -> None:
    """Write an iterable of dataclasses/dicts as NDJSON to file or stdout."""
    out = file or sys.stdout
    for r in results:
        j = json.dumps(_to_serializable(r), ensure_ascii=False)
        out.write(j + "\n")
