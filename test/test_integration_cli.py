"""
Phase 1 End-to-End Test (E2E)
Verifies that the full ./run URL_FILE command executes successfully,
produces valid NDJSON lines, and contains all required MetricResult fields.
"""

from __future__ import annotations
import json
import subprocess
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "bs" / ("run.cmd" if os.name == "nt" else "run")

def _make_test_urlfile(tmp_path: Path) -> Path:
    """Create a minimal URL file with one valid model URL."""
    f = tmp_path / "urls.txt"
    f.write_text("https://huggingface.co/bert-base-uncased\n", encoding="utf-8")
    return f

def test_cli_end_to_end(tmp_path):
    """Run ./run URL_FILE and verify NDJSON output."""
    urlfile = _make_test_urlfile(tmp_path)
    env = os.environ.copy()
    env["LOG_LEVEL"] = "1"
    proc = subprocess.run(
        [str(RUN), str(urlfile.resolve())],
        cwd=ROOT / "bs",
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )

    # CLI should succeed
    assert proc.returncode == 0, f"CLI failed: {proc.stderr}"

    # Parse NDJSON output
    lines = [l.strip() for l in proc.stdout.splitlines() if l.strip()]
    assert lines, "No output from CLI"
    results = [json.loads(l) for l in lines]

    # Required fields from MetricResult
    required = [
        "name", "category",
        "net_score", "net_score_latency",
        "ramp_up_time", "ramp_up_time_latency",
        "bus_factor", "bus_factor_latency",
        "performance_claims", "performance_claims_latency",
        "license", "license_latency",
        "size_score", "size_score_latency",
        "dataset_and_code_score", "dataset_and_code_score_latency",
        "dataset_quality", "dataset_quality_latency",
        "code_quality", "code_quality_latency",
    ]

    for result in results:
        # All required keys present
        missing = [k for k in required if k not in result]
        assert not missing, f"Missing keys: {missing}"

        # Category should be MODEL
        assert result["category"] == "MODEL"

        # Latency fields are non-negative ints
        for k in [f for f in required if "latency" in f]:
            v = result[k]
            assert isinstance(v, int) and v >= 0, f"{k} invalid: {v}"
