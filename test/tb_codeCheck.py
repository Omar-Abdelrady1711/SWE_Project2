# tests/test_code_quality_metric.py
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

from src.metrics.codeCheck import score_code_quality


# -----------------------------
# Helpers
# -----------------------------
def write(p: Path, content: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content), encoding="utf-8")


def has_git() -> bool:
    return shutil.which("git") is not None


def _git(repo: Path, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(repo),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        timeout=20,
        check=False,
    )


def init_git_repo(repo: Path, days_ago_last_commit: int = 0, extra_commits_90d: int = 2, authors_180d: int = 2) -> None:
    # initialize a tiny git repo with controlled commit dates and authors
    _git(repo, "init")
    _git(repo, "config", "user.email", "dev@example.com")
    _git(repo, "config", "user.name", "Dev")

    # first commit long ago to ensure history exists
    write(repo / "seed.txt", "seed")
    env = os.environ.copy()
    long_ago = int(time.time() - 400 * 86400)
    env.update({
        "GIT_AUTHOR_DATE": str(long_ago),
        "GIT_COMMITTER_DATE": str(long_ago),
    })
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "seed", env=env)

    # authors diversity (last 180d)
    for i in range(authors_180d):
        write(repo / f"author_{i}.txt", f"a{i}")
        env_div = os.environ.copy()
        ts = int(time.time() - 60 * 86400)  # within 180d
        env_div.update({
            "GIT_AUTHOR_DATE": str(ts),
            "GIT_COMMITTER_DATE": str(ts),
            "GIT_AUTHOR_NAME": f"A{i}",
            "GIT_AUTHOR_EMAIL": f"a{i}@ex.com",
            "GIT_COMMITTER_NAME": f"A{i}",
            "GIT_COMMITTER_EMAIL": f"a{i}@ex.com",
        })
        _git(repo, "add", ".")
        _git(repo, "commit", "-m", f"author {i}", env=env_div)

    # activity (last 90d)
    for i in range(extra_commits_90d):
        write(repo / f"recent_{i}.txt", f"r{i}")
        env_recent = os.environ.copy()
        ts = int(time.time() - 10 * 86400)  # within 90d
        env_recent.update({
            "GIT_AUTHOR_DATE": str(ts),
            "GIT_COMMITTER_DATE": str(ts),
        })
        _git(repo, "add", ".")
        _git(repo, "commit", "-m", f"recent {i}", env=env_recent)

    # ensure last commit recency matches param
    if days_ago_last_commit:
        write(repo / "touch.txt", "x")
        env_last = os.environ.copy()
        ts = int(time.time() - days_ago_last_commit * 86400)
        env_last.update({
            "GIT_AUTHOR_DATE": str(ts),
            "GIT_COMMITTER_DATE": str(ts),
        })
        _git(repo, "add", ".")
        _git(repo, "commit", "-m", "last", env=env_last)


# -----------------------------
# Fixtures
# -----------------------------
@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    return repo


# -----------------------------
# Tests
# -----------------------------

def test_minimal_repo_no_git(tmp_repo: Path):
    # No .git folder -> neutral-ish maintainer score path
    write(tmp_repo / "module.py", "def f():\n    return 1\n")
    res = score_code_quality(tmp_repo)
    assert 0.0 <= res.score <= 1.0
    # ensure latency and breakdown present
    assert res.latency_ms >= 0
    assert res.breakdown.code_clarity is not None
    # with minimal everything, score should be low-ish
    assert res.score <= 0.6


@pytest.mark.skipif(not has_git(), reason="git is required for maintainer responsiveness tests")
def test_git_activity_improves_maintainer_score(tmp_repo: Path):
    write(tmp_repo / "module.py", "def f():\n    return 1\n")
    init_git_repo(tmp_repo, days_ago_last_commit=1, extra_commits_90d=10, authors_180d=4)

    res = score_code_quality(tmp_repo)
    assert 0.0 <= res.score <= 1.0
    # maintainer responsiveness should be healthy
    assert res.breakdown.maintainer_responsiveness >= 0.5


def test_structure_signals(tmp_repo: Path):
    write(tmp_repo / "pyproject.toml", """
        [project]
        name = "demo"
        version = "0.0.1"
    """)
    write(tmp_repo / "src/pkg/__init__.py", "")
    write(tmp_repo / "src/pkg/core.py", "def g(x: int) -> int:\n    return x+1\n")
    res = score_code_quality(tmp_repo)
    # structure should contribute positively
    assert res.breakdown.structure >= 0.5


def test_tests_and_coverage(tmp_repo: Path):
    write(tmp_repo / "tests/test_basic.py", "def test_ok():\n    assert 1\n")
    write(tmp_repo / "README.md", """
        # Project
        ![coverage](https://img.shields.io/badge/coverage-85%25-green)
    """)
    write(tmp_repo / "pyproject.toml", "[tool.pytest.ini_options]\naddopts = '-q'\n")
    res = score_code_quality(tmp_repo)

    # tests present should add a big chunk
    assert res.breakdown.tests_and_coverage >= 0.4
    # coverage badge should be reflected
    assert res.breakdown.details["tests"]["coverage_badge_pct"] == 85


def test_code_clarity_docstrings_types_comments(tmp_repo: Path):
    write(tmp_repo / "README.md", "# Usage\n\nInstall\n\n## Contributing\n")
    write(tmp_repo / "pkg/__init__.py", "")
    write(tmp_repo / "pkg/mod.py", '''
        """Module docs"""

        def add(a: int, b: int) -> int:
            """Add two ints"""
            # simple comment
            return a + b
    ''')
    res = score_code_quality(tmp_repo)
    assert res.breakdown.code_clarity >= 0.4
    # docstring coverage + type hints should be recognized
    ast_stats = res.breakdown.details["clarity"]["ast_stats"]
    assert ast_stats["docstring_coverage"] > 0
    assert ast_stats["type_hint_coverage"] > 0


def test_line_length_penalty(tmp_repo: Path):
    long_line = "x" * 300
    write(tmp_repo / "pkg/bad.py", f"{long_line}\n")
    base = score_code_quality(tmp_repo)

    # now add clarity elements to isolate the penalty
    write(tmp_repo / "pkg/good.py", '''
        """Doc"""
        def f(a: int) -> int:
            """d"""
            # c
            return a
    ''')
    better = score_code_quality(tmp_repo)

    # Even after adding clarity, average line length should still penalize one of them
    # Ensure the penalty path executes without exploding the score to 1
    assert 0.0 <= base.score <= 1.0
    assert 0.0 <= better.score <= 1.0


def test_governance_ci_and_pinned_requirements(tmp_repo: Path):
    write(tmp_repo / "LICENSE", "MIT")
    write(tmp_repo / ".gitignore", "*.pyc\n__pycache__/\n")
    wf = tmp_repo / ".github" / "workflows" / "ci.yml"
    write(wf, "name: ci\n")
    write(tmp_repo / "requirements.txt", "requests==2.32.3\nnumpy>=1.26\n")
    res = score_code_quality(tmp_repo)

    gov = res.breakdown.governance_and_ci
    assert gov >= 0.3
    pinned_ratio = res.breakdown.details["governance"]["pinned_ratio"]
    assert 0.0 <= pinned_ratio <= 1.0
    assert res.breakdown.details["governance"]["has_ci_workflows"] is True


@pytest.mark.parametrize(
    "files, expect_low",
    [
        ([], True),
        ([("README.md", "# Project\n")], False),
    ],
)
def test_readme_presence_influences_clarity(tmp_repo: Path, files, expect_low):
    write(tmp_repo / "pkg/m.py", "def f():\n    pass\n")
    for rel, content in files:
        write(tmp_repo / rel, content)
    res = score_code_quality(tmp_repo)
    if expect_low:
        assert res.breakdown.code_clarity <= 0.5
    else:
        assert res.breakdown.code_clarity >= 0.2


def test_metric_result_shape(tmp_repo: Path):
    write(tmp_repo / "pkg/m.py", "def f():\n    pass\n")
    res = score_code_quality(tmp_repo)
    assert hasattr(res, "name") and res.name == "code_quality"
    assert isinstance(res.score, float)
    assert isinstance(res.latency_ms, int)
    # breakdown object has 5 components
    assert all(
        hasattr(res.breakdown, k)
        for k in [
            "maintainer_responsiveness",
            "code_clarity",
            "structure",
            "tests_and_coverage",
            "governance_and_ci",
        ]
    )
