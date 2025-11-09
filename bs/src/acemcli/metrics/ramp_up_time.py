"""
Simplified Ramp-Up Time Metric (LLM-based)
------------------------------------------
Computes only the ramp-up score based on README clarity,
using the Purdue GenAI LLM API.
"""

from __future__ import annotations
import os
import re
import time
from pathlib import Path
from typing import Dict
from dotenv import load_dotenv
import requests

from huggingface_hub import snapshot_download
from .base import register
from ..config import load_config
from ..models import MetricResult, Category

load_dotenv()
_cfg = load_config()

def _log(msg: str, level: int = 1):
    """Simple logger obeying Config log_level."""
    if _cfg.log_level >= level:
        line = f"[RampUp] {msg}"
        if _cfg.log_file:
            with open(_cfg.log_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        else:
            print(line)


# ----------------------------------------------------------------------
# Minimal LLM Client
# ----------------------------------------------------------------------
_GENAI_KEY = os.getenv("GEN_AI_STUDIO_API_KEY")
_GENAI_URL = "https://genai.rcac.purdue.edu/api/chat/completions"
_GENAI_MODEL = os.getenv("LLM_MODEL", "llama3.1:latest")


def _ask_llm(readme_text: str) -> float:
    """Query the GenAI API and return a float score [0,1]."""
    if not _GENAI_KEY:
        _log("Missing GEN_AI_STUDIO_API_KEY", 0)
        return 0.0

    payload = {
        "model": _GENAI_MODEL,
        "temperature": 0.0,
        "messages": [
            {"role": "system", "content": "Rate README clarity on a 0–1 scale."},
            {
                "role": "user",
                "content": (
                    "Rate the clarity and completeness of this README in a single number "
                    "between 0 (worst) and 1 (best). Respond with just the number.\n\n"
                    f"{readme_text[:4000]}"
                ),
            },
        ],
    }
    try:
        headers = {"Authorization": f"Bearer {_GENAI_KEY}", "Content-Type": "application/json"}
        resp = requests.post(_GENAI_URL, headers=headers, json=payload, timeout=45)
        resp.raise_for_status()
        data = resp.json()
        text = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        try:
            return float(text)
        except ValueError:
            m = re.search(r"\b(0(?:\.\d+)?|1(?:\.0+)?)\b", text)
            return float(m.group(1)) if m else 0.0
    except Exception as e:
        _log(f"LLM request failed: {e}", 0)
        return 0.0


# ----------------------------------------------------------------------
# Metric Class
# ----------------------------------------------------------------------
class RampUpTimeMetric:
    name = "ramp_up_time"

    def supports(self, url: str, category: Category) -> bool:
        return url.startswith("https://huggingface.co/")

    def compute(self, url: str, category: Category) -> MetricResult:
        """Return a MetricResult with ramp-up score populated."""
        start = time.perf_counter()
        score = 0.0

        try:
            if os.path.isabs(url) and os.path.exists(url):
                readme_path = Path(url) / "README.md"
            else:
                repo_id = url.replace("https://huggingface.co/", "").strip("/")
                local_dir = snapshot_download(
                    repo_id=repo_id,
                    allow_patterns=["README.md"],
                    local_dir_use_symlinks=False,
                )
                readme_path = Path(local_dir) / "README.md"

            if not readme_path.exists():
                _log(f"No README found for {url}", 1)
            else:
                text = readme_path.read_text(encoding="utf-8", errors="ignore")
                score = _ask_llm(text)

        except Exception as e:
            _log(f"Error processing {url}: {e}", 0)
            score = 0.0
        # finalize and return regardless of whether an exception occurred above
        latency_ms = int((time.perf_counter() - start) * 1000)
        score = max(0.0, min(1.0, score))

        _log(f"Ramp-up score for {url}: {score:.3f} ({latency_ms} ms)", 1)
        # Return a MetricResult with only the ramp_up_time fields populated.
        return MetricResult(
            name=url.replace("https://huggingface.co/", ""),
            category=("MODEL" if url.startswith("https://huggingface.co/") else "CODE"),
            ramp_up_time=score,
            ramp_up_time_latency=latency_ms,
        )


# Register this metric with the system
register(RampUpTimeMetric())
