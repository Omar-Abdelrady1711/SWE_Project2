from __future__ import annotations
from typing import Literal

Category = Literal["MODEL", "DATASET", "CODE"]


def infer_category_from_url(url: str) -> Category:
    url = (url or "").lower()
    if "huggingface.co/datasets" in url or "/datasets/" in url:
        return "DATASET"
    if "huggingface.co" in url:
        return "MODEL"
    if "github.com" in url:
        return "CODE"
    return "MODEL"


def read_urls_from_file(path: str):
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            yield line
