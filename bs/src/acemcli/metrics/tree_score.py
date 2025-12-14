from __future__ import annotations
import time
import urllib.parse
from ..models import MetricResult, Category
from .base import register
from bs.src.models_db import SessionLocal
from bs.src.lineage.models import get_parents
from bs.src.acemcli import orchestrator as orch


class TreeScoreMetric:
    name = "tree_score"

    def supports(self, url: str, category: Category) -> bool:
        return category == "MODEL"

    def _name_from_url(self, url: str) -> str:
        parsed = urllib.parse.urlparse(str(url))
        return parsed.path.rstrip("/").split("/")[-1] or str(url)

    def compute(self, url: str, category: Category) -> MetricResult:
        t0 = time.perf_counter()

        # Resolve the model identifier used in lineage edges
        model_id = self._name_from_url(url)

        # Fetch direct parents from lineage table
        session = SessionLocal()
        try:
            parents = get_parents(session, model_id)
        finally:
            session.close()

        scores: list[float] = []
        for p in parents:
            pid = p.get("parent_id")
            if not pid:
                continue
            try:
                # Treat parent_id as a URL for scoring; if it's a name, this still produces a deterministic baseline
                res = orch._compute_one(str(pid), "MODEL")
                scores.append(float(getattr(res, "net_score", 0.0)))
            except Exception:
                # If scoring a parent fails, skip it (robustness over strictness)
                continue

        score = sum(scores) / len(scores) if scores else 0.0

        latency_ms = int((time.perf_counter() - t0) * 1000)
        return MetricResult(
            name=url,
            category=category,
            tree_score=score,
            tree_score_latency=latency_ms,
        )


register(TreeScoreMetric())
