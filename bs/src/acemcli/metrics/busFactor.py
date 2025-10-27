from __future__ import annotations
import tempfile
import time
import subprocess
from pathlib import Path
from typing import Dict
from types import SimpleNamespace

try:
    from models import MetricResult, Category
except Exception:
    from dataclasses import dataclass
    from typing import Dict as _Dict
    Category = str
    @dataclass
    class MetricResult:
        name: str
        category: Category
        net_score: float; net_score_latency: int
        ramp_up_time: float; ramp_up_time_latency: int
        bus_factor: float; bus_factor_latency: int
        performance_claims: float; performance_claims_latency: int
        license: float; license_latency: int
        size_score: _Dict[str, float]; size_score_latency: int
        dataset_and_code_score: float; dataset_and_code_score_latency: int
        dataset_quality: float; dataset_quality_latency: int
        code_quality: float; code_quality_latency: int

try:
    from base import register
except Exception:
    def register(_obj: object) -> None:
        pass

#subprocess.run wrapper to ensure no errors when running git files
def _safe_run_git(repo: Path, args: list[str]) -> tuple[int, str, str]:
    try:
        p = subprocess.run(
            ["git"] + args, cwd=str(repo),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=25
        )
        return p.returncode, p.stdout, p.stderr
    except Exception as e:
        return 1, "", str(e)

#shallow clone a hugging face repo to run other functions quickly
def _clone_hf_repo(namespace: str, repo: str, dest: Path) -> tuple[bool, str]:
    url = f"https://huggingface.co/{namespace}/{repo}"
    try:
        p = subprocess.run(
            ["git","clone","--depth","400","--filter=blob:none", url, str(dest)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=120
        )
        if p.returncode != 0:
            return False, p.stderr
        return True, ""
    except FileNotFoundError:
        return False, "git not available on PATH"
    except Exception as e:
        return False, str(e)

#calculate hhi, if closer to 1 is dominated by single contributor if 0 very distributed
def _compute_concentration(commits_by_author: Dict[str, int]) -> float:
    total = sum(commits_by_author.values())
    if total <= 0:
        return 0.0
    shares = [(c/total) for c in commits_by_author.values() if c > 0]
    hhi = sum(s*s for s in shares)
    return max(0.0, min(1.0, 1.0 - hhi))

def _score_repo(repo: Path) -> float:
    now = int(time.time())
    #recency window
    since_180 = now - 180*86400

    #days since last commit
    rc, out, _ = _safe_run_git(repo, ["log","-1","--format=%ct"])
    if rc != 0 or not out.strip():
        return 0.3
    last_ts = int(out.strip())
    days_since_last = (time.time() - last_ts)/86400.0

    #commit counts / author
    rc, out, _ = _safe_run_git(repo, ["log", f"--since={since_180}", "--format=%ae"])
    authors: Dict[str,int] = {}
    if rc == 0 and out:
        for line in out.splitlines():
            a = line.strip().lower()
            if a:
                authors[a] = authors.get(a, 0) + 1
    #fallback if recent is empty
    if not authors:
        rc, out, _ = _safe_run_git(repo, ["log","--format=%ae"])
        if rc == 0 and out:
            for line in out.splitlines():
                a = line.strip().lower()
                if a:
                    authors[a] = authors.get(a, 0) + 1

    #concentration
    conc = _compute_concentration(authors)

    #diversity bonus
    diversity = max(0.0, min(1.0, len(authors)/5.0))

    #recency multiplier
    recency = max(0.0, min(1.0, 1.0 - (days_since_last/365.0)))
    
    #final calculation
    base = 0.7*conc + 0.3*diversity
    return max(0.0, min(1.0, base*recency))

#register it to registry
def supports(url: str, category: Category) -> bool:
    return url.startswith("https://huggingface.co/") and category in ("MODEL","DATASET")

def compute(url: str, category: Category) -> MetricResult:
    t0 = time.perf_counter()
    namespace, repo = url.rstrip("/").split("/")[3:5]
    bus_score = 0.3
    with tempfile.TemporaryDirectory() as tmp:
        checkout = Path(tmp)/"repo"
        ok, _ = _clone_hf_repo(namespace, repo, checkout)
        if ok and checkout.exists():
            bus_score = _score_repo(checkout)
    latency_ms = int((time.perf_counter() - t0)*1000)
    return MetricResult(
        name=f"{namespace}/{repo}", category=category,
        net_score=0.0, net_score_latency=0,
        ramp_up_time=0.0, ramp_up_time_latency=0,
        bus_factor=float(bus_score), bus_factor_latency=latency_ms,
        performance_claims=0.0, performance_claims_latency=0,
        license=0.0, license_latency=0,
        size_score={"raspberry_pi":0.0,"jetson_nano":0.0,"desktop_pc":0.0,"aws_server":0.0},
        size_score_latency=0,
        dataset_and_code_score=0.0, dataset_and_code_score_latency=0,
        dataset_quality=0.0, dataset_quality_latency=0,
        code_quality=0.0, code_quality_latency=0,
    )

# keep registry compatibility without a class
register(SimpleNamespace(name="bus_factor", supports=supports, compute=compute))
