from __future__ import annotations

import os
import re
import time
import tempfile
import subprocess
import urllib.parse
from typing import List

import requests
from huggingface_hub import ModelCard

from ..models import MetricResult, Category
from .base import register


UA = "acemcli-reproducibility/1.0"
TIMEOUT_S = float(os.getenv("REPRO_TIMEOUT_S", "20"))
MAX_BLOCKS = int(os.getenv("REPRO_MAX_BLOCKS", "3"))
MAX_INLINE_SNIPPETS = int(os.getenv("REPRO_MAX_INLINE", "3"))

GITHUB_REPO_RE = re.compile(
    r"https?://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)",
    re.IGNORECASE,
)

# Extract python -c "...." or python3 -c '....'
PYTHON_C_RE = re.compile(
    r"(?:^|\s)python(?:3)?\s+-c\s+([\"'])(.+?)\1",
    re.IGNORECASE | re.DOTALL,
)

# Inline “python-ish” lines (no fences). Anchored per-line; we group consecutive hits.
INLINE_PY_LINE_RE = re.compile(
    r"^\s*("
    r"from\s+\w[\w\.]*\s+import\s+.+|"
    r"import\s+\w[\w\.]*.*|"
    r".*pipeline\s*\(.*|"
    r".*AutoModel.*|"
    r".*AutoTokenizer.*|"
    r".*load_dataset\s*\(.*|"
    r".*model\s*=\s*.*|"
    r".*tokenizer\s*=\s*.*"
    r")\s*$",
    re.IGNORECASE,
)

# If there’s “demo guidance” but we can’t extract runnable python, treat as demo-present (0.5 if cannot run)
DEMO_GUIDANCE_RE = re.compile(
    r"(pip\s+install|conda\s+install|python\s+-m\s+\w|python\s+\w+\.py|usage\b|quickstart\b|how to use\b|example\b)",
    re.IGNORECASE,
)


def _fetch_text(url: str, timeout: float = 10.0) -> str:
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
        if r.status_code != 200:
            return ""
        return r.text or ""
    except Exception:
        return ""


def _get_github_readme(url: str) -> str:
    """
    Best-effort: fetch README from a GitHub repo URL via common raw patterns.
    """
    m = GITHUB_REPO_RE.search(url or "")
    if not m:
        return ""
    owner, repo = m.group(1), m.group(2)
    repo = repo[:-4] if repo.lower().endswith(".git") else repo

    candidates = [
        f"https://raw.githubusercontent.com/{owner}/{repo}/main/README.md",
        f"https://raw.githubusercontent.com/{owner}/{repo}/master/README.md",
        f"https://raw.githubusercontent.com/{owner}/{repo}/main/README.MD",
        f"https://raw.githubusercontent.com/{owner}/{repo}/master/README.MD",
    ]
    for c in candidates:
        txt = _fetch_text(c)
        if txt.strip():
            return txt
    return ""


def _get_hf_model_card(url: str) -> str:
    try:
        path = urllib.parse.urlparse(url).path.strip("/")
        parts = [p for p in path.split("/") if p]

        if len(parts) >= 2:
            repo_id = f"{parts[0]}/{parts[1]}"
        elif len(parts) == 1:
            repo_id = parts[0]   # <-- IMPORTANT FIX
        else:
            return ""

        card = ModelCard.load(repo_id)
        return card.text or ""
    except Exception:
        return ""



def _extract_code_blocks(text: str) -> List[str]:
    """
    Extract fenced code blocks. Prioritize python-ish blocks.
    """
    if not text:
        return []

    blocks: List[str] = []
    fence_re = re.compile(r"```(?:python|py)?\s*\n(.*?)\n```", re.DOTALL | re.IGNORECASE)
    for m in fence_re.finditer(text):
        code = (m.group(1) or "").strip()
        if code:
            blocks.append(code)

    if not blocks:
        generic_re = re.compile(r"```\s*\n(.*?)\n```", re.DOTALL)
        for m in generic_re.finditer(text):
            code = (m.group(1) or "").strip()
            if code:
                blocks.append(code)

    return blocks


def _extract_python_c_snippets(text: str) -> List[str]:
    """
    Extract python -c "...." snippets and return the inside code.
    """
    if not text:
        return []
    out: List[str] = []
    for m in PYTHON_C_RE.finditer(text):
        code = (m.group(2) or "").strip()
        if code:
            out.append(code)
    return out


def _extract_inline_python_snippets(text: str) -> List[str]:
    """
    Extract small inline python-ish snippets even if not fenced.
    We group consecutive matching lines into one snippet (up to a cap).
    """
    if not text:
        return []

    lines = text.splitlines()
    snippets: List[str] = []
    buf: List[str] = []

    for line in lines:
        if INLINE_PY_LINE_RE.search(line):
            buf.append(line.strip())
            if len(buf) >= 8:  # cap snippet size
                snippets.append("\n".join(buf).strip())
                buf = []
        else:
            if buf:
                snippets.append("\n".join(buf).strip())
                buf = []

    if buf:
        snippets.append("\n".join(buf).strip())

    # de-dupe while preserving order
    seen = set()
    uniq: List[str] = []
    for s in snippets:
        key = s.lower()
        if key not in seen and len(s) >= 10:
            seen.add(key)
            uniq.append(s)

    return uniq[:MAX_INLINE_SNIPPETS]


def _looks_like_python(code: str) -> bool:
    s = (code or "").strip()
    if not s:
        return False
    return any(tok in s for tok in ["import ", "from ", "def ", "print(", "pipeline(", "torch", "transformers"])


def _try_run_python(code: str, timeout_s: float) -> bool:
    """
    Run a python snippet in a subprocess with timeout.
    Success = exit code 0.
    """
    if not _looks_like_python(code):
        return False

    # Safer env: inherit system env, then add/strip a few keys.
    env = dict(os.environ)
    env.update(
        {
            "PYTHONUNBUFFERED": "1",
            "HF_HUB_DISABLE_TELEMETRY": "1",
            "TRANSFORMERS_NO_ADVISORY_WARNINGS": "1",
        }
    )
    # optionally strip secrets
    for k in ["GITHUB_TOKEN", "GH_TOKEN", "HF_TOKEN", "HUGGINGFACE_TOKEN", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]:
        env.pop(k, None)

    with tempfile.TemporaryDirectory() as td:
        try:
            script_path = os.path.join(td, "demo.py")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(code + "\n")

            r = subprocess.run(
                [os.environ.get("PYTHON", "python"), script_path],
                cwd=td,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=timeout_s,
            )
            return r.returncode == 0
        except Exception:
            return False


class ReproducibilityMetric:
    """
    Spec:
    - 0.0: no demo code or doesn't run
    - 0.5: demo exists but needs debugging/fixes (or we can’t execute it here)
    - 1.0: runs with no changes/debugging
    """
    name = "reproducibility"

    def supports(self, url: str, category: Category) -> bool:
        return category == "MODEL"

    def compute(self, url: str, category: Category) -> MetricResult:
        t0 = time.perf_counter()
        url_l = (url or "").lower()

        # 1) Get model card / README text
        text = ""
        if "huggingface.co" in url_l:
            text = _get_hf_model_card(url)
        if not text and "github.com" in url_l:
            text = _get_github_readme(url)

        # 2) Extract candidate demo snippets
        blocks = _extract_code_blocks(text)
        python_c = _extract_python_c_snippets(text)
        inline_snips = _extract_inline_python_snippets(text)

        # priority: fenced blocks first, then python -c, then inline
        candidates = (blocks + python_c + inline_snips)[:MAX_BLOCKS]

        if not candidates:
            # No extracted python candidates. If there is still clear “demo guidance”, treat as demo-present (0.5),
            # otherwise truly no demo (0.0).
            score = 0.5 if (text and DEMO_GUIDANCE_RE.search(text)) else 0.0
        else:
            ran_ok = any(_try_run_python(snippet, TIMEOUT_S) for snippet in candidates)
            score = 1.0 if ran_ok else 0.5

        latency_ms = int((time.perf_counter() - t0) * 1000)
        return MetricResult(
            name=url,
            category=category,
            reproducibility=float(score),
            reproducibility_latency=latency_ms,
        )


register(ReproducibilityMetric())
