# test/conftest.py
from __future__ import annotations
import sys, types, importlib, tempfile, os
from pathlib import Path

# 1) Ensure src/ is first on sys.path
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# 2) Shim the 'acemcli' package so tests that import it resolve to your local code.
#    We alias:
#      acemcli.metrics  -> src/metrics
#      acemcli.models   -> src/models  (if present) else provide a minimal stub
acemcli = sys.modules.get("acemcli")
if acemcli is None:
    acemcli = types.ModuleType("acemcli")
    sys.modules["acemcli"] = acemcli

# Map acemcli.metrics -> local metrics package
metrics_mod = importlib.import_module("acemcli.metrics")
sys.modules["acemcli.metrics"] = metrics_mod

# Map acemcli.models -> local models module if it exists; otherwise stub the bits tests need
try:
    models_mod = importlib.import_module("models")  # src/models.py
    sys.modules["acemcli.models"] = models_mod
except ModuleNotFoundError:
    # Minimal fallback so imports don't explode during collection
    from dataclasses import dataclass
    from typing import Any, Dict

    models_stub = types.ModuleType("acemcli.models")

    Category = str  # simple alias; in your project this is an Enum or Literal

    @dataclass
    class MetricResult:
        name: str
        category: Category
        net_score: float; net_score_latency: int
        ramp_up_time: float; ramp_up_time_latency: int
        bus_factor: float; bus_factor_latency: int
        performance_claims: float; performance_claims_latency: int
        license: float; license_latency: int
        size_score: Dict[str, float]; size_score_latency: int
        dataset_and_code_score: float; dataset_and_code_score_latency: int
        dataset_quality: float; dataset_quality_latency: int
        code_quality: float; code_quality_latency: int

    # Some files may import SizeScore; make it a Dict[str, float] alias.
    SizeScore = Dict[str, float]

    models_stub.Category = Category
    models_stub.MetricResult = MetricResult
    models_stub.SizeScore = SizeScore

    sys.modules["acemcli.models"] = models_stub

# 3) Stub huggingface_hub for offline tests (dataset_quality/size_score call snapshot_download)
if "huggingface_hub" not in sys.modules:
    hh = types.ModuleType("huggingface_hub")

    def snapshot_download(repo_id: str, repo_type=None, local_dir=None, **kwargs) -> str:
        d = local_dir or tempfile.mkdtemp(prefix="hf_stub_")
        os.makedirs(d, exist_ok=True)
        return d

    hh.snapshot_download = snapshot_download
    sys.modules["huggingface_hub"] = hh
