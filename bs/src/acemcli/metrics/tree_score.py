from __future__ import annotations
import time
from ..models import MetricResult, Category
from .base import register

class TreeScoreMetric:
    name = "tree_score"

    def supports(self, url: str, category: Category) -> bool:
        return category == "MODEL"

    def compute(self, url: str, category: Category) -> MetricResult:
        t0 = time.perf_counter()

        # until lineage is implemented, stable baseline default
        score = 0.7

        latency_ms = int((time.perf_counter() - t0) * 1000)
        return MetricResult(
            name=url, category=category,
            tree_score=score,
            tree_score_latency=latency_ms,
        )

register(TreeScoreMetric())
