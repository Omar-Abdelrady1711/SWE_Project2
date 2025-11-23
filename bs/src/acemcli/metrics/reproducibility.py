from __future__ import annotations
import re, time
from ..models import MetricResult, Category
from .base import register

class ReproducibilityMetric:
    name = "reproducibility"

    def supports(self, url: str, category: Category) -> bool:
        return category == "MODEL"

    def compute(self, url: str, category: Category) -> MetricResult:
        t0 = time.perf_counter()

        # super light heuristic for baseline:
        # if it’s HF or GitHub, assume partial reproducibility
        # (you can improve later by reading README from local_repo metric)
        score = 0.5
        if "github.com" in url.lower():
            score = 1.0

        latency_ms = int((time.perf_counter() - t0) * 1000)

        return MetricResult(
            name=url, category=category,
            reproducibility=score,
            reproducibility_latency=latency_ms,
        )

register(ReproducibilityMetric())
