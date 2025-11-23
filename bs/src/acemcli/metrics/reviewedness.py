from __future__ import annotations
import time
from ..models import MetricResult, Category
from .base import register

class ReviewednessMetric:
    name = "reviewedness"

    def supports(self, url: str, category: Category) -> bool:
        return category == "MODEL"

    def compute(self, url: str, category: Category) -> MetricResult:
        t0 = time.perf_counter()

        if "github.com" not in url.lower():
            score = -1.0   # spec: no github -> -1
        else:
            score = 0.7    # placeholder until you fetch PR reviews

        latency_ms = int((time.perf_counter() - t0) * 1000)
        return MetricResult(
            name=url, category=category,
            reviewedness=score,
            reviewedness_latency=latency_ms,
        )

register(ReviewednessMetric())
