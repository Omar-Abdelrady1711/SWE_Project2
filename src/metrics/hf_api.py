from __future__ import annotations
import time
from huggingface_hub import HfApi
from typing import ClassVar
# Use top-level imports so the module works when tests import `metrics` directly
from models import MetricResult, Category
from metrics.base import register
from config import load_config

class HFAPIMetric:
    name: ClassVar[str] = "hf_api"

    def __init__(self) -> None:
        cfg = load_config()
        # HfApi uses env var HF_TOKEN automatically; we also pass if present
        self.api = HfApi(token=cfg.hf_token) if cfg.hf_token else HfApi()

    def supports(self, url: str, category: Category) -> bool:
        return url.startswith("https://huggingface.co/") and category in ("MODEL", "DATASET")

    def compute(self, url: str, category: Category) -> MetricResult:
        t0 = time.perf_counter()
        namespace, repo = url.rstrip("/").split("/")[3:5]
        is_model = category == "MODEL"
        meta = (
            self.api.model_info(f"{namespace}/{repo}")
            if is_model else
            self.api.dataset_info(f"{namespace}/{repo}")
        )

        def squash(n: int, k: float = 1000.0) -> float:
            return min(1.0, n / (n + k))

        downloads = getattr(meta, "downloads", 0) or 0
        likes = getattr(meta, "likes", 0) or 0
        ramp = min(1.0, 0.3 + 0.7 * squash(likes, 100.0))
        bus  = min(1.0, 0.2 + 0.8 * squash(downloads, 10_000.0))

        latency_ms = int((time.perf_counter() - t0) * 1000)
        return MetricResult(
            name=f"{namespace}/{repo}", category=category,
            net_score=0.0, net_score_latency=0,
            ramp_up_time=ramp, ramp_up_time_latency=latency_ms,
            bus_factor=bus, bus_factor_latency=latency_ms,
            performance_claims=0.5, performance_claims_latency=latency_ms,
            license=0.5, license_latency=latency_ms,
            size_score={"raspberry_pi": 0.0, "jetson_nano": 0.0, "desktop_pc": 0.0, "aws_server": 0.0},
            size_score_latency=0,
            dataset_and_code_score=0.5, dataset_and_code_score_latency=latency_ms,
            dataset_quality=0.5, dataset_quality_latency=latency_ms,
            code_quality=0.5, code_quality_latency=latency_ms,
        )

register(HFAPIMetric())
