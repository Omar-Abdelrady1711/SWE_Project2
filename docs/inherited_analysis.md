# Inherited Repository Audit (Phase 2 Readiness)

Date: 2025-10-26
Target: `SWE_Project2` (Python package inside repo `Ece-49022`)

## Summary

- Build: PASS (no syntax errors in inspected modules)
- Tests: FAIL during collection (import/package layout mismatch)
- CLI/Orchestration: Incomplete/missing (empty `src/cli.py`, `src/scorer.py`, and utility stubs)
- Metrics: Several implemented, but inconsistent import style and result types; some likely nonfunctional at runtime

This document inventories what works, what fails, and the prioritized changes needed to reach Phase 2.

---

## Inventory of components

- Top-level project files
  - `pyproject.toml` (project `acmecli`, Python >=3.9, deps: huggingface-hub, requests, orjson; dev: pytest, mypy, etc.)
  - `pytest.ini`, `pytest` tests present under `SWE_Project2/test/` and some standalone scripts in `SWE_Project2/`.

- Library code (`SWE_Project2/src/`)
  - CLI and orchestration
    - `src/cli.py` — EMPTY (incomplete CLI)
    - `src/scorer.py` — EMPTY (no orchestration/aggregation pipeline)
    - `src/utils/parse.py` — EMPTY
    - `src/utils/output.py` — EMPTY
    - `src/config.py` — OK: env-driven config (log level, workers, HF token)
    - `src/models.py` — Defines a single dataclass `MetricResult` with many required fields (no defaults) and `Category` literal and `SizeScore` type.
  - Error handling and timeouts
    - `src/acemcli/exceptions.py` — Implemented; rich exception classes and helpers (appears functional)
    - `src/acemcli/timeout_config.py` — Implemented; central timeout config and requests session factory
  - Metrics (plugin-style)
    - Registry: `src/metrics/base.py` — OK: defines Metric protocol, registry, register/get APIs
    - Package init: `src/metrics/__init__.py` — Imports all metrics to self-register
    - Implementations:
      - `size_score.py` — Uses HF API/snapshot to estimate model weights; returns partial `MetricResult` focusing on `size_score` only
      - `licenseCheck.py` — Standalone helpers; not integrated with registry; used directly by tests
      - `dataset_quality.py` — Uses snapshot, returns only `dataset_quality` fields
      - `dataset_code_score.py` — Returns only `dataset_and_code_score` fields
      - `ramp_up_time.py` — Returns full `MetricResult` with other fields set to 0.0
      - `performance_claims.py` — Returns full `MetricResult` with other fields set to 0.0
      - `codeCheck.py` — Large implementation with its own local `MetricResult` dataclass (name collision) and a `CodeQualityMetric` that returns the shared-style `MetricResult`; also exposes a separate `score_code_quality` for local repos
      - `busFactor.py` — Implements as module-level functions; returns full `MetricResult`
      - `local_repo.py` — Simple heuristic metric, returns full `MetricResult`
      - `hf_api.py` — Uses `load_config()` but does not import it (bug); returns full `MetricResult`

- Tests
  - `SWE_Project2/test/` contains unit tests for: license detection, dataset quality, bus factor, size_score, plus a custom `conftest.py` that manipulates import paths and provides stubs for `huggingface_hub`.
  - Additional demo/verification scripts live in `SWE_Project2/` root (not pytest-style).

---

## What is currently functional

- `src/config.py` — loads config from environment; simple and correct
- `src/acemcli/exceptions.py` — ready for use, with helpers for consistency
- `src/acemcli/timeout_config.py` — configurable timeouts and retry-enabled requests session
- Metrics (static review only; see “risks”):
  - `metrics/base.py` registry utilities compile cleanly
  - `licenseCheck.py` passes isolated reasoning and is used directly by tests (no registry required)
  - `size_score.py`, `dataset_quality.py`, `dataset_code_score.py`, `ramp_up_time.py`, `performance_claims.py`, `codeCheck.py`, `busFactor.py`, `local_repo.py`, `hf_api.py` parse without syntax errors

---

## What fails or is incomplete

1) Test collection/imports (P0)
   - Running pytest fails at import time before any tests execute.
   - Error observed:
     - ImportError: attempted relative import beyond top-level package
     - Trace: `test/conftest.py -> importlib.import_module("metrics") -> src/metrics/__init__.py -> from . import base -> src/metrics/base.py -> from ..models import MetricResult`
   - Root cause: The test harness inserts `src/` on `sys.path` and then imports top-level package `metrics`. Inside `metrics/base.py`, relative import `..models` assumes `metrics` is nested under a parent package. When treated as a top-level package, `..models` goes beyond top-level and fails.

2) Incomplete CLI and orchestration (P0)
   - `src/cli.py` empty: no argument parsing, input validation, or invocation of metrics
   - `src/scorer.py` empty: no orchestration pipeline to select metrics, run with timeouts, aggregate `MetricResult`s into a `net_score`, or produce output
   - `src/utils/parse.py` and `src/utils/output.py` empty: no URL parsing, formatting, or NDJSON/CSV writer utilities

3) Inconsistent imports between modules (P0/P1)
   - Some modules import `from src.models ...` and `from src.metrics.base ...` (absolute from package root `src`)
   - Others use relative imports like `from ..models ...`
   - Tests also use mixed import paths: `acemcli.metrics...`, `src.metrics...`, and `metrics.busFactor`
   - This inconsistency breaks test collection and will break runtime depending on working directory and `PYTHONPATH`

4) `MetricResult` type inconsistency (P1)
   - Shared `src/models.py` dataclass requires many fields with no defaults. Several metric implementations only populate their own fields (e.g., `dataset_quality`, `size_score`), which would raise `TypeError` if instantiated directly.
   - `metrics/codeCheck.py` defines another dataclass also named `MetricResult` local to that module, which can create confusion and type conflicts.

5) `hf_api.py` missing import (P1)
   - Uses `load_config()` but never imports it (should import from `src.config`). Will raise `NameError` at runtime.

6) Registry integration gaps (P2)
   - `licenseCheck.py` provides helper functions but is not a `Metric` plugin nor registered via `register(...)`. It’s used only directly in tests.
   - Some metrics return partial results; orchestrator is expected to merge results, but the orchestrator is missing.

7) Test dependencies and assumptions (P2)
   - Tests rely on `git` availability for `busFactor` (fixture skips if missing)
   - Hypothesis is required (we installed it locally for audit)
   - `conftest.py` stubs out `huggingface_hub.snapshot_download`, enabling offline runs, which is good

---

## Test run evidence

Environment: Windows, Python 3.13 (workspace venv)
Command run: `pytest` (via venv)

Outcome: FAIL during collection

- First error: ImportError from `src/metrics/base.py` due to `from ..models` when importing top-level `metrics`.
- No unit tests executed; all subsequent results blocked by import failure.

---

## Gaps vs Phase 2 expectations

Phase 2 requires a working CLI, metric orchestration, timeouts, error handling, and stable outputs. Current gaps:

- Missing CLI: no `argparse` interface, no input file support, no output writers (NDJSON/JSON/CSV)
- No orchestrator: no mechanism to select supported metrics per URL, enforce `TimeoutConfig`, aggregate/scalarize results (e.g., weighted `net_score`), or handle exceptions with `acemcli.exceptions`
- Inconsistent packaging: imports and module paths not standardized; tests assert multiple import styles
- Metric result merging: need a canonical aggregator to merge per-metric outputs into a single `MetricResult` per artifact and compute `net_score`
- Missing unit tests for the CLI and orchestrator behaviors (timeouts, partial failures, output contract)

---

## Prioritized action items (Phase 2)

P0 — Must fix to unblock tests and development
1) Standardize package layout and imports
   - Choose one package root (recommend: make `src/` the package root with name `acemcli`)
   - Migrate: `src/metrics` -> `src/acemcli/metrics` (or adjust tests to import `src.metrics` consistently)
   - Update all imports to absolute under that root, e.g., `from acemcli.models import MetricResult`, `from acemcli.metrics.base import register`
   - Fix `src/metrics/base.py` to use absolute import (no `..models`)
   - Ensure `SWE_Project2/test/conftest.py` matches the chosen layout (avoid importing bare `metrics`)

2) Implement minimal orchestrator and CLI
   - Orchestrator (e.g., `src/acemcli/orchestrator.py`):
     - Load config (`TimeoutConfig`, HF token)
     - For each URL+category, gather `supported_metrics(...)` and execute with timeouts, capturing `MetricResult`s
     - Merge partial results into a canonical `MetricResult` and compute `net_score` (define weighting)
     - Robust error handling with `acemcli.exceptions`; continue on per-metric failures
   - CLI (`src/cli.py`):
     - argparse: input file or URLs, output format, concurrency, timeouts
     - Calls orchestrator; writes NDJSON or table via `utils/output.py`

P1 — Correctness and coherence
3) Unify `MetricResult`
   - Make all fields optional with defaults, or provide a builder/merger that fills missing fields
   - Remove the duplicate `MetricResult` definition in `codeCheck.py` (rename to avoid collision or reuse the shared model)
   - Add helper to merge metric-specific partials into one `MetricResult`

4) Fix `hf_api.py`
   - Add `from src.config import load_config` (or `from acemcli.config import load_config`) and validate token handling

5) Registry integration
   - Convert `licenseCheck.py` into a proper plugin or keep as utility; if a plugin, provide `supports/compute` and call `register(...)`

P2 — DevEx, reliability, documentation
6) Utilities
   - `utils/parse.py`: URL/category parsing, validation; mapping GitHub/HF URLs to category
   - `utils/output.py`: NDJSON/JSON/CSV writers; pretty table for console

7) Tests
   - Add tests for CLI args, orchestrator flow, timeout behavior, partial metric failures, and output contract
   - Stabilize `conftest.py` to align with the final package name and import strategy

8) Performance and network hygiene
   - Prefer metadata API over `snapshot_download` when possible (size_score does this already); respect `TimeoutConfig`

---

## Suggested import strategy (concrete)

- Adopt `acemcli` as the single top-level package (matches `pyproject.toml`):
  - Move modules under `src/acemcli/` (metrics, models, config, utils)
  - Use absolute imports everywhere, e.g., `from acemcli.models import MetricResult`
  - Update tests to import `acemcli.metrics...` (or adjust `conftest.py` shims accordingly)

If moving files is out-of-scope now, minimally:
- Change `src/metrics/base.py` to `from models import MetricResult, Category`
- Change other metrics using `from src.models ...` to `from models ...` for test harmony
- Or modify `test/conftest.py` to import `src.metrics` instead of bare `metrics`

---

## Quality gates (current status)

- Build: PASS (modules parse; no syntax errors in reviewed files)
- Lint/Typecheck: NOT RUN (mypy strict configured; expect failures due to empty modules and partial `MetricResult` usage)
- Tests: FAIL (import error during collection as detailed above)

---

## Notes

- Git required for `busFactor` tests (fixture skips if missing). On this machine, git is available.
- We installed `pytest` and `hypothesis` in the local venv to attempt a run. The import error prevents further execution.
- `huggingface_hub` calls are stubbed by the test harness; network access is not required for unit tests.
