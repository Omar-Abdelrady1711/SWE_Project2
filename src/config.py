from __future__ import annotations
import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Config:
    # logging
    log_level: int     # 0,1,2
    log_file: str | None

    # execution
    workers: int       # >0

    # auth
    hf_token: str | None

def _int_env(name: str, default: int) -> int:
    try:
        v = int(os.environ.get(name, "").strip() or default)
        return v if v > 0 else default
    except Exception:
        return default

def load_config() -> Config:
    lvl = os.environ.get("LOG_LEVEL", "0").strip()
    # clamp to 0/1/2
    log_level = 0
    if lvl in {"1", "2"}: log_level = int(lvl)

    log_file = os.environ.get("LOG_FILE") or None
    workers = _int_env("ACME_WORKERS", 8)
    hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN") or None
    return Config(log_level=log_level, log_file=log_file, workers=workers, hf_token=hf_token)
