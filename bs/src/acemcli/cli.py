from __future__ import annotations
import sys
import logging
from pathlib import Path
from urllib.parse import urlparse

from acemcli.logging_setup import setup_logging
from acemcli.config import load_config
from acemcli.orchestrator import compute_all, to_ndjson
from acemcli.models import Category  # should be Literal["model","dataset","code"]

log = logging.getLogger(__name__)

def infer_category(url: str) -> Category:
    # Return canonical Category literals (uppercase) used across the codebase
    if "/datasets/" in url:
        return "DATASET"
    if url.startswith("https://huggingface.co/"):
        return "MODEL"
    return "CODE"

def _is_valid_url(s: str) -> bool:
    try:
        u = urlparse(s)
        return u.scheme in {"http", "https"} and bool(u.netloc)
    except Exception:
        return False

def main(url_file: str) -> int:
    setup_logging()
    cfg = load_config()
    log.info("starting run: workers=%s log_level=%s", getattr(cfg, "workers", "?"), getattr(cfg, "log_level", "?"))

    p = Path(url_file)
    # Accept relative paths too; resolve to absolute
    if not p.exists():
        print("URL_FILE must point to an existing file", file=sys.stderr)
        return 1
    p = p.resolve()

    # read, strip, drop comments and empties
    raw_lines = p.read_text(encoding="utf-8").splitlines()
    lines = []
    seen = set()
    for ln in raw_lines:
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        if s not in seen:
            seen.add(s)
            lines.append(s)

    # build (url, category) pairs; compute only for models per spec
    pairs: list[tuple[str, Category]] = []
    for s in lines:
        if not _is_valid_url(s):
            log.warning("skipping invalid URL: %s", s)
            continue
        cat = infer_category(s)
        # compute only for models per spec
        if cat == "MODEL":
            pairs.append((s, cat))

    results, errors = compute_all(pairs)
    for res in results:
        # print one NDJSON line per model
        print(to_ndjson(res))

    # If we computed at least one result, treat the run as successful even if
    # some per-URL metric computations failed (they are logged). Only fail if
    # nothing was produced.
    if not results:
        if errors:
            print(f"{len(errors)} URL(s) failed. See logs for details.", file=sys.stderr)
        else:
            print("No results produced.", file=sys.stderr)
        return 1

    if errors:
        log.warning("%d URL(s) had metric errors; results printed for successful URLs", len(errors))
    return 0

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m acemcli.cli /path/to/URL_FILE", file=sys.stderr)
        raise SystemExit(1)
    raise SystemExit(main(sys.argv[1]))
