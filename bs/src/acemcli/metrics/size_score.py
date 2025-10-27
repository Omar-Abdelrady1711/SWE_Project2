from __future__ import annotations
import math
import time as tm
import logging as logmod
from pathlib import Path
from urllib.parse import urlparse
from tempfile import TemporaryDirectory

from huggingface_hub import HfApi, snapshot_download

from ..models import MetricResult, Category, SizeScore
from .base import register

log = logmod.getLogger(__name__)

# device thresholds (MB)
THRESHOLDS_MB = {
    "raspberry_pi": 50,
    "jetson_nano": 200,
    "desktop_pc": 2000,
    "aws_server": 10000,
}

# weight-like files
WEIGHT_EXTS = (".safetensors", ".bin", ".onnx", ".pt", ".ckpt", ".h5", ".gguf")

# score curve params (no smoothstep)
S_KNEE   = 0.60   # score exactly at r = 1.0
PLATEAU  = 0.45   # score at the end of the grace band
TOL      = 0.15   # 15% grace over the device threshold
GAMMA    = 1.0    # concavity for in-budget ramp (>=1 is fine)
DECAY_K  = 1.6    # exponential decay rate when well over budget


def hf_model_slug(url: str):
    parts = urlparse(url).path.strip("/").split("/")
    if len(parts) < 2:
        raise ValueError("Bad HF model URL")
    return parts[0], parts[1]

def size_mb_via_api(owner: str, name: str) -> int | None:
    try:
        api = HfApi()
        info = api.model_info(f"{owner}/{name}", timeout=8.0)
        total = 0
        matched = False
        for sib in getattr(info, "siblings", []) or []:
            rfn = getattr(sib, "rfilename", "") or ""
            sz  = getattr(sib, "size", None)
            if isinstance(sz, int) and any(rfn.endswith(ext) for ext in WEIGHT_EXTS):
                total += sz; matched = True
        if matched:
            return int(total / 1_000_000)  
    except Exception as e:
        log.debug("size_score API fallback: %s", e)
    return None

def size_mb_via_snapshot(owner: str, name: str) -> int | None:
    try:
        with TemporaryDirectory() as tmp:
            local = snapshot_download(
                repo_id=f"{owner}/{name}",
                repo_type="model",
                local_dir=tmp,
                local_dir_use_symlinks=False,
                allow_patterns=[f"*{ext}" for ext in WEIGHT_EXTS],
            )
            p = Path(local)
            total = 0
            matched = False
            for f in p.rglob("*"):
                if f.is_file() and any(str(f).endswith(ext) for ext in WEIGHT_EXTS):
                    try:
                        total += f.stat().st_size; matched = True
                    except Exception:
                        pass
            if matched:
                return int(total / 1_000_000)
    except Exception as e:
        log.warning("size_score snapshot failed: %s/%s: %s", owner, name, e)
    return None

def device_score(size_mb: int, max_mb: int) -> float:
    """
    Piecewise (continuous):

      r = size_mb / max_mb

      1) In budget (r <= 1):
         s = S_KNEE + (1 - r)^GAMMA * (1 - S_KNEE)
            # 1.0 at r=0 → S_KNEE at r=1

      2) Slightly oversize (1 < r <= 1+TOL):
         s = S_KNEE - (S_KNEE - PLATEAU) * ((r - 1) / TOL)
            # linear drop from S_KNEE to PLATEAU

      3) Clearly oversize (r > 1+TOL):
         s = PLATEAU * exp(-DECAY_K * (r - (1 + TOL)))
            # exponential decay from PLATEAU downward

      All three branches meet continuously at r=1 and r=1+TOL.
    """
    if max_mb <= 0:
        return 0.0
    r = size_mb / float(max_mb)

    if r <= 1.0:
        s = S_KNEE + (1.0 - r) ** GAMMA * (1.0 - S_KNEE)
    elif r <= 1.0 + TOL:
        s = S_KNEE - (S_KNEE - PLATEAU) * ((r - 1.0) / TOL)
    else:
        s = PLATEAU * math.exp(-DECAY_K * (r - (1.0 + TOL)))

    return round(0.0 if s < 0.0 else 1.0 if s > 1.0 else s, 2)

def scores_from_mb(size_mb: int) -> SizeScore:
    return {
        "raspberry_pi": device_score(size_mb, THRESHOLDS_MB["raspberry_pi"]),
        "jetson_nano":  device_score(size_mb, THRESHOLDS_MB["jetson_nano"]),
        "desktop_pc":   device_score(size_mb, THRESHOLDS_MB["desktop_pc"]),
        "aws_server":   device_score(size_mb, THRESHOLDS_MB["aws_server"]),
    }

class SizeScoreMetric:
    name = "size_score"

    def supports(self, url, category: Category):
        return category == "MODEL" and url.startswith("https://huggingface.co/")

    def compute(self, url, category: Category):
        t0 = tm.perf_counter()
        owner, name = hf_model_slug(url)

        size_mb = size_mb_via_api(owner, name)
        if size_mb is None:
            size_mb = size_mb_via_snapshot(owner, name)

        if size_mb is None:
            score_obj: SizeScore = {k: 0.5 for k in THRESHOLDS_MB}  # neutral fallback
        else:
            score_obj = scores_from_mb(size_mb)

        latency_ms = int((tm.perf_counter() - t0) * 1000)
        return MetricResult(
            name=f"{owner}/{name}",
            category=category,
            size_score=score_obj,
            size_score_latency=latency_ms,
        )

register(SizeScoreMetric())
