from __future__ import annotations
import tempfile, time
from pathlib import Path
from huggingface_hub import snapshot_download
from acemcli.models import MetricResult, Category
from acemcli.metrics.base import register

class LocalRepoMetric:
    name = "local_repo"

    def supports(self, url: str, category: Category) -> bool:
        return url.startswith("https://huggingface.co/") and category in ("MODEL", "DATASET")

    def compute(self, url: str, category: Category) -> MetricResult:
        t0 = time.perf_counter()
        namespace, repo = url.rstrip("/").split("/")[3:5]
        with tempfile.TemporaryDirectory() as tmp:
            local_dir = snapshot_download(repo_id=f"{namespace}/{repo}", local_dir=tmp, local_dir_use_symlinks=False)
            p = Path(local_dir)
            files = [f for f in p.rglob("*") if f.is_file()]
            readme = next((f for f in files if f.name.lower().startswith("readme")), None)
            has_examples = any(
                "example" in f.name.lower() or (f.suffix in {".ipynb", ".py"} and "test" in f.name.lower())
                for f in files
            )

        ramp = 0.8 if readme else 0.3
        dataset_and_code = 0.9 if has_examples else 0.4
        code_quality = 0.6
        dataset_quality = 0.5

        latency_ms = int((time.perf_counter() - t0) * 1000)
        return MetricResult(
            name=f"{namespace}/{repo}", category=category,
            net_score=0.0, net_score_latency=0,
            ramp_up_time=ramp, ramp_up_time_latency=latency_ms,
            bus_factor=0.5, bus_factor_latency=latency_ms,
            performance_claims=0.5, performance_claims_latency=latency_ms,
            license=0.5, license_latency=latency_ms,
            size_score={"raspberry_pi": 0.0, "jetson_nano": 0.0, "desktop_pc": 0.0, "aws_server": 0.0},
            size_score_latency=0,
            dataset_and_code_score=dataset_and_code, dataset_and_code_score_latency=latency_ms,
            dataset_quality=dataset_quality, dataset_quality_latency=latency_ms,
            code_quality=code_quality, code_quality_latency=latency_ms,
        )

register(LocalRepoMetric())
