from __future__ import annotations
import logging
from acemcli.config import load_config

def setup_logging() -> None:
    cfg = load_config()
    level_map = {0: logging.CRITICAL, 1: logging.INFO, 2: logging.DEBUG}
    lvl = level_map.get(getattr(cfg, "log_level", 0), logging.CRITICAL)

    handlers = []
    if getattr(cfg, "log_file", None):
        fh = logging.FileHandler(cfg.log_file, encoding="utf-8")
        fh.setLevel(lvl)
        handlers.append(fh)

    sh = logging.StreamHandler()
    sh.setLevel(lvl)
    handlers.append(sh)

    logging.basicConfig(
        level=lvl,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )
