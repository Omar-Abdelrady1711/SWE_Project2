from __future__ import annotations
from typing import Dict, Iterable
import orjson
from pathlib import Path


def to_ndjson_line(d: Dict) -> str:
    return orjson.dumps(d).decode("utf-8")


def write_ndjson(path: str | Path, items: Iterable[Dict]) -> None:
    p = Path(path)
    with p.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(to_ndjson_line(it) + "\n")


def pretty_print_metric(res) -> None:
    # Simple console print for MetricResult-like objects
    try:
        print(f"{res.name} [{res.category}] net={res.net_score:.3f} (ramp={res.ramp_up_time:.3f}, bus={res.bus_factor:.3f})")
    except Exception:
        print(str(res))
