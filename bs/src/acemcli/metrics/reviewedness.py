from __future__ import annotations

import os
import re
import time
import urllib.parse
from typing import Optional, Tuple, Set

import requests
from huggingface_hub import hf_hub_download

from ..models import MetricResult, Category
from .base import register


# ---------- config ----------
DEFAULT_MAX_PRS = int(os.getenv("REVIEWEDNESS_MAX_PRS", "60"))
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
UA = "acemcli-reviewedness/1.0"

# GitHub repo URL regex
GITHUB_RE = re.compile(r"https?://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)", re.IGNORECASE)

# extensions to exclude as "weights / binaries / non-code"
EXCLUDE_EXTS: Set[str] = {
    ".safetensors", ".bin", ".pt", ".pth", ".ckpt", ".onnx", ".h5", ".gguf",
    ".npy", ".npz", ".parquet", ".arrow", ".feather",
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp",
    ".mp4", ".mov", ".avi", ".mkv",
    ".pdf", ".zip", ".tar", ".gz", ".7z",
}

# treat as code if extension is in this set OR if it's a well-known code filename
CODE_EXTS: Set[str] = {
    ".py", ".ipynb", ".js", ".ts", ".tsx", ".java", ".kt", ".go", ".rs", ".cpp", ".c", ".h",
    ".cs", ".php", ".rb", ".swift",
    ".sh", ".bash", ".ps1",
    ".yml", ".yaml", ".toml", ".ini", ".cfg",
    ".json", ".md", ".rst", ".txt",
    ".sql",
}

CODE_FILENAMES = {"dockerfile", "makefile", "cmakelists.txt"}


# ---------- helpers ----------
def _gh_headers() -> dict[str, str]:
    h = {"Accept": "application/vnd.github+json", "User-Agent": UA}
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h


def _gh_get(url: str, timeout: float = 10.0) -> requests.Response:
    return requests.get(url, headers=_gh_headers(), timeout=timeout)


def _extract_github_repo_from_text(text: str) -> Optional[Tuple[str, str]]:
    m = GITHUB_RE.search(text or "")
    if not m:
        return None
    owner, repo = m.group(1), m.group(2)
    repo = repo[:-4] if repo.lower().endswith(".git") else repo
    return owner, repo


def _repo_from_url(url: str) -> Optional[Tuple[str, str]]:
    url = (url or "").strip()
    if not url:
        return None

    # direct github URL
    m = GITHUB_RE.search(url)
    if m:
        owner, repo = m.group(1), m.group(2)
        repo = repo[:-4] if repo.lower().endswith(".git") else repo
        return owner, repo

    # huggingface URL -> read README.md and extract github link
    if url.startswith("https://huggingface.co/"):
        path = urllib.parse.urlparse(url).path.strip("/")
        parts = [p for p in path.split("/") if p]
        repo_id = None
        if len(parts) >= 2:
            repo_id = f"{parts[0]}/{parts[1]}"
        elif len(parts) == 1:
            repo_id = parts[0]

        if repo_id:
            try:
                readme_path = hf_hub_download(repo_id=repo_id, filename="README.md")
                with open(readme_path, "r", encoding="utf-8", errors="ignore") as f:
                    return _extract_github_repo_from_text(f.read())
            except Exception:
                return None

    return None


def _is_code_file(path: str) -> bool:
    p = (path or "").lower()
    base = p.rsplit("/", 1)[-1]

    if base in CODE_FILENAMES:
        return True

    # extension
    dot = base.rfind(".")
    ext = base[dot:] if dot != -1 else ""
    if ext in EXCLUDE_EXTS:
        return False
    return ext in CODE_EXTS


def _pr_has_review(sess: requests.Session, owner: str, repo: str, pr_number: int) -> bool:
    r = sess.get(
        f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/reviews?per_page=100",
        headers=_gh_headers(),
        timeout=10.0,
    )
    if r.status_code != 200:
        return False
    data = r.json()
    return isinstance(data, list) and len(data) > 0


def _pr_code_changed(sess: requests.Session, owner: str, repo: str, pr_number: int) -> int:
    """
    Sum (additions+deletions) for CODE FILES ONLY in this PR.
    Uses GitHub PR files endpoint which includes per-file additions/deletions.
    """
    total = 0
    page = 1
    while True:
        r = sess.get(
            f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files?per_page=100&page={page}",
            headers=_gh_headers(),
            timeout=10.0,
        )
        if r.status_code != 200:
            break
        files = r.json()
        if not files:
            break

        for f in files:
            filename = f.get("filename") or ""
            if not _is_code_file(filename):
                continue
            adds = int(f.get("additions") or 0)
            dels = int(f.get("deletions") or 0)
            total += (adds + dels)

        page += 1

    return total


def _reviewedness(owner: str, repo: str, max_prs: int) -> float:
    sess = requests.Session()

    reviewed_code = 0
    total_code = 0

    page = 1
    seen = 0

    while True:
        r = sess.get(
            f"https://api.github.com/repos/{owner}/{repo}/pulls?state=closed&per_page=100&page={page}",
            headers=_gh_headers(),
            timeout=10.0,
        )
        if r.status_code != 200:
            # repo exists but API failed/rate-limited -> be conservative
            return 0.0

        pulls = r.json()
        if not pulls:
            break

        for pr in pulls:
            if seen >= max_prs:
                break
            seen += 1

            if not pr.get("merged_at"):
                continue

            number = pr.get("number")
            if not number:
                continue

            changed = _pr_code_changed(sess, owner, repo, int(number))
            if changed <= 0:
                continue

            total_code += changed
            if _pr_has_review(sess, owner, repo, int(number)):
                reviewed_code += changed

        if seen >= max_prs:
            break
        page += 1

    if total_code == 0:
        return 0.0
    score = reviewed_code / float(total_code)
    return 0.0 if score < 0.0 else 1.0 if score > 1.0 else score


# ---------- metric ----------
class ReviewednessMetric:
    """
    Spec:
    - reviewedness = fraction of all code (not weights) introduced via PRs WITH a code review
    - if no linked GitHub repo -> -1
    """
    name = "reviewedness"

    def supports(self, url: str, category: Category) -> bool:
        return category == "MODEL"

    def compute(self, url: str, category: Category) -> MetricResult:
        t0 = time.perf_counter()

        repo_ref = _repo_from_url(url)
        if not repo_ref:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            return MetricResult(
                name=url,
                category=category,
                reviewedness=-1.0,
                reviewedness_latency=latency_ms,
            )

        owner, repo = repo_ref
        try:
            score = float(_reviewedness(owner, repo, DEFAULT_MAX_PRS))
        except Exception:
            score = 0.0

        latency_ms = int((time.perf_counter() - t0) * 1000)
        return MetricResult(
            name=url,
            category=category,
            reviewedness=score,
            reviewedness_latency=latency_ms,
        )


register(ReviewednessMetric())
