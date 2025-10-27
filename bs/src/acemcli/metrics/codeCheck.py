from __future__ import annotations
import ast
import json
import logging
import os
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from huggingface_hub import snapshot_download
from acemcli.models import MetricResult, Category
from acemcli.metrics.base import register


@dataclass
class MetricBreakdown:
    maintainer_responsiveness: float
    code_clarity: float
    structure: float
    tests_and_coverage: float
    governance_and_ci: float
    details: Dict[str, object]


@dataclass
class MetricResult:
    name: str
    score: float
    latency_ms: int
    breakdown: MetricBreakdown


def _safe_run_git(repo: Path, args: List[str]) -> Tuple[int, str, str]:
    try:
        p = subprocess.run(
            ["git"] + args,
            cwd=str(repo),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
        return p.returncode, p.stdout, p.stderr
    except Exception as e:
        return 1, "", str(e)


def _git_recent_activity_score(repo: Path) -> Tuple[float, Dict[str, object]]:
    """
    Score maintainer responsiveness using git history:
      - commits_last_90d (normalized)
      - unique_authors_180d (normalized)
      - days_since_last_commit (inverted)
    """
    details = {}
    # Default if no git
    if not (repo / ".git").exists():
        return 0.3, {"note": "No git history found (.git missing)"}  # neutral-ish

    # Last commit date (unix)
    rc, out, _ = _safe_run_git(repo, ["log", "-1", "--format=%ct"])
    if rc != 0 or not out.strip():
        return 0.3, {"note": "Unable to read git history"}
    last_commit_ts = int(out.strip())
    days_since_last = (time.time() - last_commit_ts) / 86400.0

    # Commits last 90 days
    since_90 = int(time.time() - 90 * 86400)
    rc, out, _ = _safe_run_git(repo, ["rev-list", "--count", f"--since={since_90}", "HEAD"])
    commits_90 = int(out.strip()) if rc == 0 and out.strip().isdigit() else 0

    # Unique authors last 180 days
    since_180 = int(time.time() - 180 * 86400)
    rc, out, _ = _safe_run_git(
        repo,
        ["log", f"--since={since_180}", "--format=%ae"]
    )
    authors = set()
    if rc == 0 and out:
        for line in out.splitlines():
            line = line.strip().lower()
            if line:
                authors.add(line)

    # Normalize components
    # Heuristics: 0–1 via soft thresholds
    def clamp01(x: float) -> float:
        return max(0.0, min(1.0, x))

    # More recent is better: 0 days -> 1.0, 365+ -> 0.0
    recency = clamp01(1.0 - (days_since_last / 365.0))
    # Commits: 50+ in 90d ~ 1.0
    commit_rate = clamp01(commits_90 / 50.0)
    # Authors: 5+ in 180d ~ 1.0
    diversity = clamp01(len(authors) / 5.0)

    score = 0.45 * recency + 0.35 * commit_rate + 0.20 * diversity
    details.update(
        dict(
            days_since_last_commit=round(days_since_last, 2),
            commits_last_90d=commits_90,
            unique_authors_last_180d=len(authors),
            components=dict(recency=recency, commit_rate=commit_rate, diversity=diversity),
        )
    )
    return score, details


def _iter_python_files(root: Path) -> List[Path]:
    return [p for p in root.rglob("*.py") if p.is_file() and ".venv" not in str(p)]


def _analyze_python_ast(files: List[Path]) -> Dict[str, float]:
    """
    Returns:
      - docstring_coverage: defs/classes with docstrings / total defs/classes
      - type_hint_coverage: fraction of function args+returns annotated
      - comment_ratio: comment lines / code lines
      - avg_line_len, max_line_len
    """
    total_defs = 0
    defs_with_doc = 0
    annotated_slots = 0
    total_slots = 0
    comment_lines = 0
    code_lines = 0
    total_len = 0
    total_lines_counted = 0
    max_len = 0

    for file in files:
        try:
            src = file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        # line stats
        for line in src.splitlines():
            s = line.strip()
            if not s:
                continue
            if s.startswith("#"):
                comment_lines += 1
            else:
                code_lines += 1
            ln = len(line)
            total_len += ln
            total_lines_counted += 1
            if ln > max_len:
                max_len = ln

        try:
            tree = ast.parse(src)
        except Exception:
            continue

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                total_defs += 1
                if ast.get_docstring(node):
                    defs_with_doc += 1

            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Return annotation
                total_slots += 1
                if node.returns is not None:
                    annotated_slots += 1
                # Arg annotations
                for arg in list(node.args.args) + list(getattr(node.args, "kwonlyargs", [])):
                    total_slots += 1
                    if arg.annotation is not None:
                        annotated_slots += 1
                if node.args.vararg is not None:
                    total_slots += 1
                    if node.args.vararg.annotation is not None:
                        annotated_slots += 1
                if node.args.kwarg is not None:
                    total_slots += 1
                    if node.args.kwarg.annotation is not None:
                        annotated_slots += 1

    doc_cov = (defs_with_doc / total_defs) if total_defs else 0.0
    type_cov = (annotated_slots / total_slots) if total_slots else 0.0
    comment_ratio = (comment_lines / max(1, (comment_lines + code_lines)))
    avg_len = (total_len / total_lines_counted) if total_lines_counted else 0.0

    return dict(
        docstring_coverage=doc_cov,
        type_hint_coverage=type_cov,
        comment_ratio=comment_ratio,
        avg_line_len=avg_len,
        max_line_len=max_len,
    )


def _readme_quality(repo: Path) -> Tuple[float, Dict[str, object]]:
    """
    Simple README score: presence + key sections.
    """
    candidates = list(repo.glob("README*"))
    if not candidates:
        return 0.0, {"readme": "missing"}

    content = ""
    try:
        content = candidates[0].read_text(encoding="utf-8", errors="ignore")
    except Exception:
        pass

    present = {
        "installation": bool(re.search(r"\binstall(ation)?\b", content, re.IGNORECASE)),
        "usage": bool(re.search(r"\busage|example(s)?\b", content, re.IGNORECASE)),
        "license": bool(re.search(r"\blicense\b", content, re.IGNORECASE)),
        "contributing": bool(re.search(r"\bcontribut(ing|ion)\b", content, re.IGNORECASE)),
        "badges": bool(re.search(r"\bcoverage|build|ci\b", content, re.IGNORECASE)),
    }
    score = sum(present.values()) / 5.0
    return score, {"readme_file": str(candidates[0].name), "sections_found": present}


def _tests_and_coverage(repo: Path) -> Tuple[float, Dict[str, object]]:
    """
    Enhanced test analysis:
      - Tests directory structure and organization
      - Test file quantity and quality indicators
      - Coverage badges and configuration
      - Test framework usage and best practices
    """
    details = {}
    
    # Test directory analysis
    has_tests_dir = (repo / "tests").exists()
    test_files = [p for p in _iter_python_files(repo) 
                  if p.name.startswith("test_") or p.name.endswith("_test.py")]
    test_dir_files = []
    
    if has_tests_dir:
        test_dir_files = [p for p in (repo / "tests").rglob("*.py") if p.is_file()]
    
    total_test_files = len(test_files) + len(test_dir_files)
    tests_present = total_test_files > 0
    
    # Test file quality analysis
    test_quality_indicators = {
        "has_conftest": any(f.name == "conftest.py" for f in test_files + test_dir_files),
        "has_fixtures": False,
        "has_parametrized_tests": False,
        "has_mock_usage": False,
        "test_organization": "poor"
    }
    
    # Analyze test file content for quality indicators
    for test_file in (test_files + test_dir_files)[:10]:  # Limit analysis for performance
        try:
            content = test_file.read_text(encoding="utf-8", errors="ignore").lower()
            if "fixture" in content or "@pytest.fixture" in content:
                test_quality_indicators["has_fixtures"] = True
            if "parametrize" in content or "@pytest.mark.parametrize" in content:
                test_quality_indicators["has_parametrized_tests"] = True
            if "mock" in content or "patch" in content:
                test_quality_indicators["has_mock_usage"] = True
        except Exception:
            continue
    
    # Test organization scoring
    if has_tests_dir and len(test_dir_files) > 5:
        test_quality_indicators["test_organization"] = "excellent"
    elif has_tests_dir or total_test_files > 3:
        test_quality_indicators["test_organization"] = "good"
    elif total_test_files > 0:
        test_quality_indicators["test_organization"] = "basic"
    
    # Coverage analysis
    coverage_pct = None
    readme_files = list(repo.glob("README*"))
    if readme_files:
        try:
            txt = readme_files[0].read_text(encoding="utf-8", errors="ignore")
            # Look for various coverage badge formats
            patterns = [
                r"(\d{1,3})\s*%\s*coverage",
                r"coverage[^0-9]*(\d{1,3})",
                r"badge.*coverage.*(\d{1,3})"
            ]
            for pattern in patterns:
                m = re.search(pattern, txt, re.IGNORECASE)
                if m:
                    coverage_pct = min(100, max(0, int(m.group(1))))
                    break
        except Exception:
            pass

    # Enhanced config analysis
    cfg_files = {
        "pyproject.toml": 0.3,
        "pytest.ini": 0.2,
        "tox.ini": 0.15,
        ".coveragerc": 0.15,
        "setup.cfg": 0.1,
        "conftest.py": 0.1
    }
    
    config_score = 0.0
    present_cfg = {}
    for cfg_file, weight in cfg_files.items():
        exists = (repo / cfg_file).exists() if cfg_file != "conftest.py" else any(
            f.name == cfg_file for f in test_files + test_dir_files
        )
        present_cfg[cfg_file] = exists
        if exists:
            config_score += weight

    # Enhanced scoring with quality factors
    score = 0.0
    
    # Base test presence (40%)
    if tests_present:
        score += 0.4
        # Bonus for test quantity
        if total_test_files >= 10:
            score += 0.1
        elif total_test_files >= 5:
            score += 0.05
    
    # Test quality bonus (20%)
    quality_bonus = 0.0
    quality_bonus += 0.05 if test_quality_indicators["has_conftest"] else 0
    quality_bonus += 0.05 if test_quality_indicators["has_fixtures"] else 0
    quality_bonus += 0.05 if test_quality_indicators["has_parametrized_tests"] else 0
    quality_bonus += 0.05 if test_quality_indicators["has_mock_usage"] else 0
    score += quality_bonus
    
    # Coverage bonus (25%)
    if coverage_pct is not None:
        score += 0.25 * (coverage_pct / 100.0)
    elif "coverage" in str(present_cfg).lower():
        score += 0.1  # Small bonus for coverage config without badge
    
    # Configuration bonus (15%)
    score += 0.15 * config_score

    details.update({
        "tests_present": tests_present,
        "has_tests_dir": has_tests_dir,
        "total_test_files": total_test_files,
        "test_files_in_root": len(test_files),
        "test_files_in_dir": len(test_dir_files),
        "coverage_badge_pct": coverage_pct,
        "configs_present": present_cfg,
        "test_quality_indicators": test_quality_indicators,
        "config_score": round(config_score, 3),
        "quality_bonus": round(quality_bonus, 3)
    })
    
    return min(1.0, score), details


def _structure_score(repo: Path, py_files: List[Path]) -> Tuple[float, Dict[str, object]]:
    has_pyproject = (repo / "pyproject.toml").exists()
    has_setup_cfg = (repo / "setup.cfg").exists() or (repo / "setup.py").exists()
    has_src_layout = (repo / "src").exists()
    has_package_init = any(p.name == "__init__.py" for p in py_files)
    # simple packaging/structure score
    score = (
        0.35 * (1.0 if has_pyproject else 0.0)
        + 0.15 * (1.0 if has_setup_cfg else 0.0)
        + 0.30 * (1.0 if has_src_layout else 0.0)
        + 0.20 * (1.0 if has_package_init else 0.0)
    )
    return score, dict(
        has_pyproject=has_pyproject,
        has_setup_cfg=has_setup_cfg,
        has_src_layout=has_src_layout,
        has_package_init=has_package_init,
    )


def _governance_ci_score(repo: Path) -> Tuple[float, Dict[str, object]]:
    has_license = any((repo / name).exists() for name in ["LICENSE", "LICENSE.md", "LICENSE.txt"])
    has_ci = (repo / ".github" / "workflows").exists()
    has_gitignore = (repo / ".gitignore").exists()
    # pinned deps (==) in requirements*.txt
    req_files = list(repo.glob("requirements*.txt"))
    pinned_count = 0
    total_deps = 0
    for f in req_files:
        try:
            for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                total_deps += 1
                if "==" in s:
                    pinned_count += 1
        except Exception:
            pass
    pinned_ratio = (pinned_count / total_deps) if total_deps else 0.0

    score = (
        0.40 * (1.0 if has_license else 0.0)
        + 0.30 * (1.0 if has_ci else 0.0)
        + 0.15 * (1.0 if has_gitignore else 0.0)
        + 0.15 * pinned_ratio
    )
    return score, dict(
        has_license=has_license,
        has_ci_workflows=has_ci,
        has_gitignore=has_gitignore,
        requirements_files=[str(p.name) for p in req_files],
        pinned_ratio=round(pinned_ratio, 2),
    )


def _code_clarity_score(repo: Path, py_files: List[Path]) -> Tuple[float, Dict[str, object]]:
    """Enhanced code clarity analysis with more sophisticated metrics."""
    ast_stats = _analyze_python_ast(py_files)
    readme_score, readme_det = _readme_quality(repo)
    
    # Enhanced complexity analysis
    complexity_stats = _analyze_complexity(py_files)
    
    # Security analysis
    security_issues = _analyze_security_patterns(py_files)
    
    # Code style and consistency analysis
    style_issues = _analyze_code_style(py_files)

    # Penalize extremely long lines (over 120 avg -> bad)
    line_length_penalty = 0.0
    if ast_stats["avg_line_len"] > 120:
        line_length_penalty = min(0.4, (ast_stats["avg_line_len"] - 120) / 200.0)
    
    # Complexity penalty
    complexity_penalty = 0.0
    if complexity_stats["complexity_ratio"] > 0.3:  # More than 30% complex functions
        complexity_penalty = min(0.2, complexity_stats["complexity_ratio"] - 0.3)
    
    # Security penalty
    security_penalty = 0.0
    total_security_issues = sum(security_issues.values())
    if total_security_issues > 0:
        security_penalty = min(0.3, total_security_issues * 0.05)

    # Enhanced weighting with more factors
    score = (
        0.35 * ast_stats["docstring_coverage"] +      # Reduced weight
        0.25 * ast_stats["type_hint_coverage"] +      # Reduced weight
        0.15 * ast_stats["comment_ratio"] +           # Maintained
        0.15 * readme_score +                         # Maintained
        0.10 * (1.0 - complexity_stats["complexity_ratio"])  # New: complexity bonus
    )
    
    # Apply penalties
    score = max(0.0, score - line_length_penalty - complexity_penalty - security_penalty)

    details = {
        "ast_stats": ast_stats,
        "readme": readme_det,
        "complexity_stats": complexity_stats,
        "security_issues": security_issues,
        "style_issues": style_issues,
        "penalties": {
            "line_length": round(line_length_penalty, 3),
            "complexity": round(complexity_penalty, 3),
            "security": round(security_penalty, 3)
        }
    }
    return score, details


def _analyze_code_style(py_files: List[Path]) -> Dict[str, object]:
    """Analyze code style and consistency issues."""
    style_issues = {
        "long_lines": 0,
        "short_variable_names": 0,
        "missing_blank_lines": 0,
        "trailing_whitespace": 0,
        "inconsistent_quotes": 0
    }
    
    for file in py_files[:20]:  # Limit for performance
        try:
            content = file.read_text(encoding="utf-8", errors="ignore")
            lines = content.splitlines()
            
            for i, line in enumerate(lines):
                # Long lines
                if len(line) > 120:
                    style_issues["long_lines"] += 1
                
                # Trailing whitespace
                if line.rstrip() != line:
                    style_issues["trailing_whitespace"] += 1
                
                # Short variable names (simple heuristic)
                words = re.findall(r'\b[a-z_][a-z0-9_]{1,2}\b', line.lower())
                style_issues["short_variable_names"] += len([w for w in words if len(w) <= 2])
            
            # Inconsistent quotes (simple check)
            single_quotes = content.count("'")
            double_quotes = content.count('"')
            if single_quotes > 0 and double_quotes > 0:
                style_issues["inconsistent_quotes"] += 1
                
        except Exception:
            continue
    
    return style_issues


def score_code_quality(repo_path: str | Path) -> MetricResult:
    """
    Compute a 0–1 score with breakdown:
      - maintainer_responsiveness (git recency, commits, authors)
      - code_clarity (docstrings, type hints, comments, README)
      - structure (packaging/layout signals)
      - tests_and_coverage (tests present, coverage badge, configs)
      - governance_and_ci (license, CI, gitignore, pinned deps)
    """
    t0 = time.time()
    repo = Path(repo_path).resolve()

    py_files = _iter_python_files(repo)

    maint_score, maint_det = _git_recent_activity_score(repo)
    clarity_score, clarity_det = _code_clarity_score(repo, py_files)
    struct_score, struct_det = _structure_score(repo, py_files)
    tests_score, tests_det = _tests_and_coverage(repo)
    gov_score, gov_det = _governance_ci_score(repo)

    # weights sum to 1.0
    weights = {
        "maintainer_responsiveness": 0.20,
        "code_clarity": 0.20,
        "structure": 0.20,
        "tests_and_coverage": 0.30,
        "governance_and_ci": 0.10,
    }

    final = (
        weights["maintainer_responsiveness"] * maint_score
        + weights["code_clarity"] * clarity_score
        + weights["structure"] * struct_score
        + weights["tests_and_coverage"] * tests_score
        + weights["governance_and_ci"] * gov_score
    )
    latency_ms = int((time.time() - t0) * 1000)

    breakdown = MetricBreakdown(
        maintainer_responsiveness=round(maint_score, 3),
        code_clarity=round(clarity_score, 3),
        structure=round(struct_score, 3),
        tests_and_coverage=round(tests_score, 3),
        governance_and_ci=round(gov_score, 3),
        details={
            "maintainer": maint_det,
            "clarity": clarity_det,
            "structure": struct_det,
            "tests": tests_det,
            "governance": gov_det,
            "weights": weights,
        },
    )
    return MetricResult(
        name="code_quality",
        score=round(max(0.0, min(1.0, final)), 3),
        latency_ms=latency_ms,
        breakdown=breakdown,
    )


class CodeQualityMetric:
    """
    Enhanced Code Quality Metric for ACME CLI
    
    Evaluates code repositories across multiple dimensions:
    - Maintainer responsiveness (git activity, community health)
    - Code clarity (documentation, type hints, readability)
    - Structure (packaging, organization, best practices)
    - Tests and coverage (test presence, quality, coverage)
    - Governance and CI (licensing, automation, dependency management)
    - Security and complexity (vulnerability patterns, code complexity)
    """
    
    name = "code_quality"
    
    def supports(self, url: str, category: Category) -> bool:
        """Check if this metric supports the given URL and category."""
        return category == "CODE" or (
            url.startswith("https://huggingface.co/") and 
            category in ("MODEL", "DATASET")
        )
    
    def compute(self, url: str, category: Category) -> MetricResult:
        """Compute the code quality score for the given repository."""
        start_time = time.perf_counter()
        
        try:
            # Extract namespace and repo name from URL
            url_parts = url.rstrip("/").split("/")
            if len(url_parts) >= 2:
                namespace, repo = url_parts[-2:]
            else:
                namespace, repo = url_parts[-1], "unknown"
            
            repo_id = f"{namespace}/{repo}" if repo != "unknown" else namespace
            
            logging.info(f"Computing code quality score for {repo_id}")
            
            # Download repository for analysis
            with tempfile.TemporaryDirectory() as tmp_dir:
                local_dir = snapshot_download(
                    repo_id=repo_id,
                    local_dir=tmp_dir,
                    local_dir_use_symlinks=False
                )
                
                code_quality_score = self._analyze_code_quality(Path(local_dir))
                
        except Exception as e:
            logging.error(f"Error computing code quality score for {url}: {e}")
            code_quality_score = 0.0
            namespace, repo = "unknown", "unknown"
            repo_id = f"{namespace}/{repo}"
        
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        
        # Return a complete MetricResult object
        return MetricResult(
            name=repo_id,
            category=category,
            net_score=0.0,  # Will be calculated by orchestrator
            net_score_latency=0,
            ramp_up_time=0.0,  # Not calculated by this metric
            ramp_up_time_latency=0,
            bus_factor=0.0,  # Not calculated by this metric
            bus_factor_latency=0,
            performance_claims=0.0,  # Not calculated by this metric
            performance_claims_latency=0,
            license=0.0,  # Not calculated by this metric
            license_latency=0,
            size_score={"raspberry_pi": 0.0, "jetson_nano": 0.0, "desktop_pc": 0.0, "aws_server": 0.0},
            size_score_latency=0,
            dataset_and_code_score=0.0,  # Not calculated by this metric
            dataset_and_code_score_latency=0,
            dataset_quality=0.0,  # Not calculated by this metric
            dataset_quality_latency=0,
            code_quality=code_quality_score,
            code_quality_latency=latency_ms,
        )
    
    def _analyze_code_quality(self, repo_path: Path) -> float:
        """Analyze the repository for code quality factors."""
        py_files = _iter_python_files(repo_path)
        
        # Get individual component scores
        maint_score, maint_det = _git_recent_activity_score(repo_path)
        clarity_score, clarity_det = _code_clarity_score(repo_path, py_files)
        struct_score, struct_det = _structure_score(repo_path, py_files)
        tests_score, tests_det = _tests_and_coverage(repo_path)
        gov_score, gov_det = _governance_ci_score(repo_path)
        
        # Enhanced weights with more focus on maintainability
        weights = {
            "maintainer_responsiveness": 0.25,  # Increased importance
            "code_clarity": 0.25,  # Increased importance
            "structure": 0.15,  # Reduced
            "tests_and_coverage": 0.25,  # Maintained high importance
            "governance_and_ci": 0.10,  # Maintained
        }
        
        final_score = (
            weights["maintainer_responsiveness"] * maint_score +
            weights["code_clarity"] * clarity_score +
            weights["structure"] * struct_score +
            weights["tests_and_coverage"] * tests_score +
            weights["governance_and_ci"] * gov_score
        )
        
        logging.debug(f"Code quality components - maintainer: {maint_score:.3f}, "
                     f"clarity: {clarity_score:.3f}, structure: {struct_score:.3f}, "
                     f"tests: {tests_score:.3f}, governance: {gov_score:.3f}")
        logging.debug(f"Final code quality score: {final_score:.3f}")
        
        return min(1.0, max(0.0, final_score))


# Register the metric
register(CodeQualityMetric())


# --- Enhanced helper functions ---

def _analyze_complexity(py_files: List[Path]) -> Dict[str, float]:
    """Analyze code complexity metrics."""
    total_functions = 0
    complex_functions = 0
    total_classes = 0
    deep_inheritance = 0
    
    for file in py_files:
        try:
            src = file.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(src)
        except Exception:
            continue
            
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                total_functions += 1
                # Simple complexity: count nested structures
                complexity = len([n for n in ast.walk(node) 
                                if isinstance(n, (ast.If, ast.For, ast.While, ast.Try))])
                if complexity > 5:  # Threshold for complex functions
                    complex_functions += 1
                    
            elif isinstance(node, ast.ClassDef):
                total_classes += 1
                # Check inheritance depth
                if len(node.bases) > 2:
                    deep_inheritance += 1
    
    complexity_ratio = (complex_functions / total_functions) if total_functions else 0.0
    inheritance_ratio = (deep_inheritance / total_classes) if total_classes else 0.0
    
    return {
        "complexity_ratio": complexity_ratio,
        "inheritance_ratio": inheritance_ratio,
        "total_functions": total_functions,
        "total_classes": total_classes
    }


def _analyze_security_patterns(py_files: List[Path]) -> Dict[str, object]:
    """Analyze code for potential security issues."""
    security_issues = {
        "eval_usage": 0,
        "exec_usage": 0,
        "shell_injection": 0,
        "sql_injection": 0,
        "hardcoded_secrets": 0
    }
    
    for file in py_files:
        try:
            src = file.read_text(encoding="utf-8", errors="ignore")
            src_lower = src.lower()
            
            # Check for dangerous patterns
            if 'eval(' in src_lower:
                security_issues["eval_usage"] += 1
            if 'exec(' in src_lower:
                security_issues["exec_usage"] += 1
            if 'os.system(' in src_lower or 'subprocess.call(' in src_lower:
                security_issues["shell_injection"] += 1
            if 'execute(' in src_lower and ('select' in src_lower or 'insert' in src_lower):
                security_issues["sql_injection"] += 1
            if any(secret in src_lower for secret in ['password=', 'secret=', 'api_key=']):
                security_issues["hardcoded_secrets"] += 1
                
        except Exception:
            continue
    
    return security_issues


# --- Optional: CLI shim for local testing ---
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Score code quality of a local repo.")
    ap.add_argument("repo", help="Path to local repository checkout")
    ap.add_argument("--ndjson", action="store_true", help="Print NDJSON line with score and breakdown")
    args = ap.parse_args()

    result = score_code_quality(args.repo)
    if args.ndjson:
        print(json.dumps({
            "metric": result.name,
            "score": result.score,
            "latency_ms": result.latency_ms,
            "breakdown": asdict(result.breakdown),
        }))
    else:
        print(f"Score: {result.score} (latency {result.latency_ms} ms)")
        print(json.dumps(asdict(result.breakdown), indent=2))
