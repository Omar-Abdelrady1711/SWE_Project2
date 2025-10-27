
from __future__ import annotations
import time as tm
import logging as logmod
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlparse

from huggingface_hub import snapshot_download

# project imports
from ..models import MetricResult, Category
from .base import register 

KEYS = ("train", "test", "validation", "split", "license", "citation", "doi", "benchmark")
ALLOW = ["README*", "readme*"]

log = logmod.getLogger(__name__)


# ----- small helper funcs (no heavy annotations) -----
def hf_dataset_slug(url):
    """owner/name from a Hugging Face DATASET url."""
    parts = urlparse(url).path.strip("/").split("/")
    if len(parts) < 3 or parts[0].lower() != "datasets":
        raise ValueError("Bad HF dataset URL")
    owner, name = parts[1], parts[2]
    return owner, name


def get_readme_text(owner, name):
    """download just README files for speed; return text or ''"""
    txt = ""
    try:
        with TemporaryDirectory() as tmp:
            local = snapshot_download(
                repo_id=f"{owner}/{name}",
                repo_type="dataset",
                local_dir=tmp,
                local_dir_use_symlinks=False,
                allow_patterns=ALLOW,
            )
            p = Path(local)
            cands = list(p.glob("README*")) + list(p.glob("readme*"))
            if cands:
                txt = cands[0].read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        logmod.getLogger(__name__).warning("dataset_quality snapshot failed: %s/%s: %s", owner, name, e)
    return txt


def score_from_text(text):
    """simple presence-based scoring on KEYS → [0,1]"""
    t = (text or "").lower()
    hits = sum(1 for k in KEYS if k in t)
    base = 0.3  # neutral base
    return max(0.0, min(1.0, base + 0.7 * (hits / max(1, len(KEYS)))))


# ----- metric class kept tiny; just wires helpers -----
class DatasetQualityMetric:
    name = "dataset_quality"

    def supports(self, url, category: Category):
        return category == "DATASET" and url.startswith("https://huggingface.co/")

    def compute(self, url, category: Category):
        t0 = tm.perf_counter()

        owner, name = hf_dataset_slug(url)
        readme = get_readme_text(owner, name)
        score = score_from_text(readme)

        latency_ms = int((tm.perf_counter() - t0) * 1000)

        # Only set this metric’s fields so other metrics can fill theirs.
        return MetricResult(
            name=f"{owner}/{name}",
            category=category,
            dataset_quality=score,
            dataset_quality_latency=latency_ms,
        )


# register on import
register(DatasetQualityMetric())

