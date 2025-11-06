from __future__ import annotations
from typing import Iterable, List, Tuple, Literal
from pathlib import Path

Category = Literal["MODEL", "DATASET", "CODE"]


def parse_url_to_category(url: str) -> Category:
    """Heuristic mapping from URL to Category.

    - huggingface.co -> MODEL or DATASET (caller should provide more context if available)
    - repositories with typical code hosting -> CODE
    """
    u = url.lower()
    if u.startswith("https://huggingface.co/"):
        # default to MODEL when ambiguous; caller may override
        return "MODEL"
    if "github.com" in u or u.endswith(".git"):
        return "CODE"
    return "CODE"


def read_pairs_from_file(path: str | Path) -> List[Tuple[str, Category]]:
    """Read lines of URL (optionally with a category suffix) from a file.

    Lines may be:
      https://huggingface.co/foo/bar
      https://huggingface.co/foo/bar,MODEL
    Empty lines and lines starting with # are ignored.
    """
    pairs: List[Tuple[str, Category]] = []
    p = Path(path)
    for ln in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        if "," in ln:
            url, cat = [x.strip() for x in ln.split(",", 1)]
            cat = cat.upper()
            if cat not in ("MODEL", "DATASET", "CODE"):
                cat = parse_url_to_category(url)
        else:
            url = ln
            cat = parse_url_to_category(url)
        pairs.append((url, cat))
    return pairs
