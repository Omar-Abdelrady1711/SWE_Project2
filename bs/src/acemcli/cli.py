from __future__ import annotations
import sys, logging
from pathlib import Path
from urllib.parse import urlparse
from acmecli.logging_setup import setup_logging
from acmecli.config import load_config
from acmecli.orchestrator import compute_all, to_ndjson
from acmecli.models import Category

log = logging.getLogger(__name__)

def infer_category(url: str) -> Category:
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
    log.info("starting run: workers=%d log_level=%d", cfg.workers, cfg.log_level)

    p = Path(url_file)
    if not p.is_absolute() or not p.exists():
        print("URL_FILE must be an absolute path to an existing file", file=sys.stderr)
        return 1

    # read, strip, drop comments and empties
    raw_lines = p.read_text(encoding="utf-8").splitlines()
    cleaned = []
    for ln in raw_lines:
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        cleaned.append(s)

    # dedupe while preserving order
    seen = set()
    lines: list[str] = []
    for s in cleaned:
        if s not in seen:
            seen.add(s)
            lines.append(s)

    # build (url, category) pairs, model-only for compute/output
    pairs: list[tuple[str, Category]] = []
    for ln in lines:
        if not _is_valid_url(ln):
            log.warning("skipping invalid URL: %s", ln)
            continue
        cat = infer_category(ln)
        if cat == "MODEL":
            pairs.append((ln, cat))

    results, errors = compute_all(pairs)
    for res in results:
        sys.stdout.buffer.write(to_ndjson(res))

    if errors:
        print(f"{len(errors)} URL(s) failed. See logs for details.", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m acmecli.cli /absolute/path/to/URL_FILE", file=sys.stderr)
        raise SystemExit(1)
    raise SystemExit(main(sys.argv[1]))
