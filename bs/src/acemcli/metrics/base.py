# main/src/metrics/base.py
from __future__ import annotations
import logging, re
from typing import Protocol, runtime_checkable, ClassVar, Dict, List, Iterable, Optional
from ..models import MetricResult, Category  # <- fixed import

logger = logging.getLogger(__name__)

@runtime_checkable
class Metric(Protocol):
    """Interface all metric plugins must implement."""
    name: ClassVar[str]

    def supports(self, url: str, category: Category) -> bool: ...
    def compute(self, url: str, category: Category) -> MetricResult: ...

# Registry keyed by metric name (prevents duplicates)
_REGISTRY: Dict[str, Metric] = {}

# Keep names stable & printable in logs/NDJSON
_NAME_RE = re.compile(r"^[a-z0-9_][a-z0-9_.-]{1,63}$", re.IGNORECASE)

def register(metric: Metric) -> None:
    """
    Register a metric plugin.
    - Enforces the Metric protocol at runtime
    - Validates name format
    - Prevents duplicate registrations
    """
    if not isinstance(metric, Metric):
        raise TypeError(f"{metric!r} does not satisfy Metric protocol")

    name = getattr(metric, "name", None)
    if not isinstance(name, str) or not _NAME_RE.match(name):
        raise ValueError(f"Metric.name must match {_NAME_RE.pattern!r} (got {name!r})")

    if name in _REGISTRY:
        raise ValueError(f"Metric '{name}' already registered")

    _REGISTRY[name] = metric
    logger.info("Registered metric '%s' (total=%d)", name, len(_REGISTRY))

def register_many(metrics: Iterable[Metric]) -> None:
    """Convenience to register multiple metrics at once."""
    for m in metrics:
        register(m)

def all_metrics() -> List[Metric]:
    """Snapshot of all registered metrics (unsorted)."""
    return list(_REGISTRY.values())

def get_metric(name: str) -> Optional[Metric]:
    """Lookup a single metric by name."""
    return _REGISTRY.get(name)

def supported_metrics(url: str, category: Category) -> List[Metric]:
    """Filter metrics that support this (url, category)."""
    mets = [m for m in _REGISTRY.values() if m.supports(url, category)]
    logger.debug("Supported metrics for %s (%s): %s", url, category, [m.name for m in mets])
    return mets

# Testing utility
def clear_registry_for_tests() -> None:
    """Clear the registry (useful to isolate unit tests)."""
    _REGISTRY.clear()
