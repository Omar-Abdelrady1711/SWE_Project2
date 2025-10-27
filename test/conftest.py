# test/conftest.py
from __future__ import annotations
import sys, pathlib, importlib, types

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG_ROOT = ROOT / "bs" / "src"

# 1) Ensure bs/src is first on sys.path
if PKG_ROOT.exists():
    sys.path.insert(0, str(PKG_ROOT))

# 2) If a stray 'acemcli' module (not a package) is already imported, drop it
if "acemcli" in sys.modules and not hasattr(sys.modules["acemcli"], "__path__"):
    del sys.modules["acemcli"]

# 3) Import real packages
metrics_pkg = importlib.import_module("acemcli.metrics")
models_pkg  = importlib.import_module("acemcli.models")   # <-- add this

# 4) Legacy compatibility aliases
sys.modules["metrics"] = metrics_pkg

# Create 'src' namespace so "from src.metrics ..." works
src_pkg = types.ModuleType("src")
src_pkg.__path__ = [str(PKG_ROOT)]
sys.modules["src"] = src_pkg
sys.modules["src.metrics"] = metrics_pkg
sys.modules["src.models"]  = models_pkg   # <-- and this
