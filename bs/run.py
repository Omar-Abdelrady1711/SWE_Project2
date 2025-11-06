#!/usr/bin/env python3
"""Bootstrapper for tests: call the package CLI from bs/ directory.
This file mirrors the top-level `run` behavior for the test harness on Windows.
"""
import sys
from pathlib import Path

# ensure package import path: bs/src on sys.path
ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    # Insert bs/src at front so `import acemcli` succeeds when run from bs/
    sys.path.insert(0, str(SRC))

def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: run URL_FILE", file=sys.stderr)
        return 1
    url_file = argv[1]
    try:
        from acemcli.cli import main as cli_main
    except Exception as e:
        print(f"Failed to import acemcli.cli: {e}", file=sys.stderr)
        return 1
    return cli_main(url_file)

if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
