# tests/test_bus_factor.py
from __future__ import annotations
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from hypothesis import given, strategies as st, assume, settings

import pytest

# Import your bus factor module (adjust if it lives in a package)
import metrics.busFactor as bf


# --------- Helpers ---------

def has_git() -> bool:
    try:
        subprocess.run(["git", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except Exception:
        return False


@pytest.fixture(autouse=True)
def _skip_if_no_git():
    if not has_git():
        pytest.skip("git not available on PATH; skipping bus-factor tests")


def init_repo() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="bf_repo_"))
    subprocess.run(["git", "init"], cwd=tmp, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # default identity to avoid global config dependency
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp, check=True)
    return tmp


def make_commit(repo: Path, filename: str, content: str,
                author_email: str, author_name: str = "Anon",
                days_ago: int = 0) -> None:
    """
    Create a commit with a specific author and backdated by 'days_ago'.
    """
    (repo / filename).write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", filename], cwd=repo, check=True)

    # Backdate the commit deterministically using env vars
    now = int(time.time())
    ts = now - days_ago * 86400
    date_str = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(ts))

    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": author_name,
        "GIT_AUTHOR_EMAIL": author_email,
        "GIT_COMMITTER_NAME": author_name,
        "GIT_COMMITTER_EMAIL": author_email,
        "GIT_AUTHOR_DATE": date_str + " +0000",
        "GIT_COMMITTER_DATE": date_str + " +0000",
    }
    subprocess.run(["git", "commit", "-m", f"Add {filename}"], cwd=repo, check=True, env=env)


# --------- Tests ---------

def test_supports_urls_and_categories():
    assert bf.supports("https://huggingface.co/user/model", "MODEL")
    assert bf.supports("https://huggingface.co/user/dataset", "DATASET")
    assert not bf.supports("https://github.com/user/repo", "MODEL")
    assert not bf.supports("https://huggingface.co/user/model", "OTHER")


def test_single_author_recent_repo_low_score():
    repo = init_repo()
    try:
        # 3 recent commits, same author
        make_commit(repo, "a.txt", "1", "alice@example.com", "Alice", days_ago=1)
        make_commit(repo, "b.txt", "2", "alice@example.com", "Alice", days_ago=1)
        make_commit(repo, "c.txt", "3", "alice@example.com", "Alice", days_ago=0)

        score = bf._score_repo(repo)  # using internal helper intentionally
        # With 1 author: conc ~ 0, diversity ~ 0.2, recency ~ 1 => ~ 0.06
        assert 0.03 <= score <= 0.15
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_five_authors_balanced_recent_high_score():
    repo = init_repo()
    try:
        # 5 authors, 1 commit each, all recent
        authors = [f"a{i}@ex.com" for i in range(5)]
        for i, email in enumerate(authors):
            make_commit(repo, f"f{i}.txt", str(i), email, f"A{i}", days_ago=0)

        score = bf._score_repo(repo)
        # For 5 equal authors: conc = 1 - sum((1/5)^2*5) = 0.8; diversity=1; recency≈1
        # base = 0.7*0.8 + 0.3*1 = 0.86
        assert 0.80 <= score <= 0.95
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_stale_repo_zero_recency_zero_score():
    repo = init_repo()
    try:
        # last commit older than 365 days -> recency -> 0
        make_commit(repo, "old.txt", "old", "old@example.com", "Old", days_ago=400)
        score = bf._score_repo(repo)
        assert score == 0.0
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_no_commits_returns_default_on_compute(monkeypatch):
    """
    simulate compute() path with an empty repo by bypassing clone
    and invoking the scoring on an empty history (log -1 will fail).
    Expect default ~0.3 from compute's neutral fallback when scoring can't run.
    """
    # Monkeypatch clone to create an empty repo without commits
    def fake_clone(ns, r, dest):
        dest.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init"], cwd=dest, check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True, ""

    monkeypatch.setattr(bf, "_clone_hf_repo", fake_clone)

    # compute() expects an HF URL; category can be a simple str (fallback Category)
    res = bf.compute("https://huggingface.co/x/y", "MODEL")
    assert hasattr(res, "bus_factor")
    # Default neutral score used when log reading fails
    assert 0.25 <= res.bus_factor <= 0.35
    assert isinstance(res.bus_factor_latency, int)


def test_concentration_helper_bounds():
    # empty -> 0.0
    assert bf._compute_concentration({}) == 0.0
    # one author -> 0.0 (fully concentrated)
    assert bf._compute_concentration({"a": 10}) == 0.0
    # two equal authors -> 1 - (0.5^2 + 0.5^2) = 0.5
    assert abs(bf._compute_concentration({"a": 5, "b": 5}) - 0.5) < 1e-6

# --- More Bus Factor tests ---

def test_email_case_insensitive_counts():
    repo = init_repo()
    try:
        # Same human, different email case -> should collapse to one author
        make_commit(repo, "a.txt", "1", "ALICE@EX.COM", "Alice", days_ago=0)
        make_commit(repo, "b.txt", "2", "alice@ex.com", "Alice", days_ago=0)
        score = bf._score_repo(repo)

        # With one unique author, score should be low (but >0 due to diversity 0.2 and recency ~1)
        assert 0.03 <= score <= 0.15
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_two_authors_highly_skewed_distribution_recent():
    repo = init_repo()
    try:
        # Alice 9 commits, Bob 1 commit -> very concentrated
        for i in range(9):
            make_commit(repo, f"a{i}.txt", str(i), "alice@ex.com", "Alice", days_ago=0)
        make_commit(repo, "b.txt", "x", "bob@ex.com", "Bob", days_ago=0)

        score = bf._score_repo(repo)
        # conc = 1 - (0.9^2 + 0.1^2) = 0.18; diversity = 0.4; base ~ 0.246; recency ~ 1
        assert 0.20 <= score <= 0.30
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_recency_exactly_365_days_clamps_to_zero():
    repo = init_repo()
    try:
        # Single commit exactly 365 days ago -> recency -> 0 => score must be 0
        make_commit(repo, "old.txt", "x", "a@ex.com", "A", days_ago=365)
        score = bf._score_repo(repo)
        assert score == 0.0
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_compute_clone_failure_uses_neutral_default(monkeypatch):
    # Force clone to fail: compute should return ~0.3 neutral
    monkeypatch.setattr(bf, "_clone_hf_repo", lambda *_: (False, "boom"))
    res = bf.compute("https://huggingface.co/u/r", "MODEL")
    assert 0.25 <= res.bus_factor <= 0.35


def test_supports_rejects_non_hf_and_wrong_category():
    assert not bf.supports("https://github.com/user/repo", "MODEL")
    assert not bf.supports("https://huggingface.co/user/model", "OTHER")


def test_concentration_helper_various_distributions():
    # one author -> 0.0
    assert bf._compute_concentration({"a": 10}) == 0.0
    # 75/25 split -> 1 - (0.75^2 + 0.25^2) = 0.375
    assert abs(bf._compute_concentration({"a": 3, "b": 1}) - 0.375) < 1e-6
    # three equal authors -> 1 - 3*(1/3)^2 = 1 - 1/3 = 2/3
    assert abs(bf._compute_concentration({"a": 1, "b": 1, "c": 1}) - (2/3)) < 1e-6


def test_recent_window_empty_but_history_exists_older_than_180_within_365():
    repo = init_repo()
    try:
        # 200 days ago (empty recent window) -> fallback to full history
        make_commit(repo, "oldish.txt", "x", "a@ex.com", "A", days_ago=200)
        score = bf._score_repo(repo)
        # recency ≈ 1 - 200/365 ≈ 0.45; base (one author) small; final score low but >0
        assert 0.01 <= score <= 0.20
    finally:
        shutil.rmtree(repo, ignore_errors=True)

# ====================== Property-based tests (Hypothesis) ======================
from hypothesis import given, strategies as st

def _base_score_from_counts(counts: list[int]) -> float:
    """
    Reproduce the base component used by _score_repo (before recency):
      base = 0.7 * conc + 0.3 * diversity
    where:
      conc = 1 - HHI over commit shares
      diversity = min(1.0, num_authors / 5.0)
    """
    counts = [c for c in counts if c > 0]
    if not counts:
        return 0.0
    conc = bf._compute_concentration({str(i): c for i, c in enumerate(counts)})
    diversity = min(1.0, len(counts) / 5.0)
    return 0.7 * conc + 0.3 * diversity


@given(st.lists(st.integers(min_value=0, max_value=100), min_size=1, max_size=25))
def test_concentration_bounds_and_permutation_invariance(counts):
    """
    For any non-negative counts:
    - concentration is within [0, 1].
    - reordering authors does not change concentration (symmetry).
    """
    d = {str(i): c for i, c in enumerate(counts) if c > 0}
    conc1 = bf._compute_concentration(d)
    assert 0.0 <= conc1 <= 1.0

    # Permute counts and check invariance
    rev = list(reversed(counts))
    d2 = {str(i): c for i, c in enumerate(rev) if c > 0}
    conc2 = bf._compute_concentration(d2)
    assert abs(conc1 - conc2) < 1e-12


@given(
    st.lists(st.integers(min_value=1, max_value=20), min_size=1, max_size=10)
    .filter(lambda xs: sum(xs) >= 2)  # need at least 2 commits total to move one
)
def test_base_score_monotonic_when_splitting_top_author(counts):
    """
    If we take 1 commit from the largest author and move it to a *new* author,
    the base score (0.7*conc + 0.3*diversity) should not decrease.

    Rationale:
      - HHI decreases when a dominant share is split -> conc increases.
      - Diversity never decreases when adding a new author (caps at 5).
    """
    counts = [int(c) for c in counts]
    counts.sort(reverse=True)

    # find an index we can decrement by 1
    idx = next(i for i, c in enumerate(counts) if c >= 1)
    counts_before = counts.copy()

    # new distribution: remove 1 from the max author, add a new author with 1 commit
    counts_after = counts.copy()
    counts_after[idx] -= 1
    counts_after.append(1)

    # sanitize (drop any zeros to match repo logic)
    before = [c for c in counts_before if c > 0]
    after = [c for c in counts_after if c > 0]

    base1 = _base_score_from_counts(before)
    base2 = _base_score_from_counts(after)

    # Allow a tiny epsilon for float math
    assert base2 + 1e-12 >= base1


@given(
    st.lists(st.integers(min_value=1, max_value=50), min_size=2, max_size=10),
    st.integers(min_value=1, max_value=10)
)
def test_concentration_improves_when_moving_commit_from_heavy_to_light(counts, delta):
    """
    If we move 'delta' commits from the strictly-heaviest author to the strictly-lightest author,
    and the move reduces the gap without overshooting equality, HHI must not increase
    (i.e., concentration = 1-HHI must not decrease).
    """
    counts = sorted([int(c) for c in counts], reverse=True)
    hi_idx, lo_idx = 0, len(counts) - 1

    # Require a strict gap; if equal, moving makes things *less* equal.
    assume(counts[hi_idx] > counts[lo_idx])

    # Keep donor non-zero and avoid overshoot; only move up to half the gap.
    gap = counts[hi_idx] - counts[lo_idx]
    max_delta_to_reduce_gap = gap // 2
    assume(max_delta_to_reduce_gap >= 1)

    # Bound the move: 1..min(max_delta_to_reduce_gap, donor-1)
    delta = min(delta, max_delta_to_reduce_gap, counts[hi_idx] - 1)
    assume(delta >= 1)

    new_counts = counts.copy()
    new_counts[hi_idx] -= delta
    new_counts[lo_idx] += delta

    conc1 = bf._compute_concentration({str(i): c for i, c in enumerate(counts) if c > 0})
    conc2 = bf._compute_concentration({str(i): c for i, c in enumerate(new_counts) if c > 0})

    assert conc2 + 1e-12 >= conc1

def test_concentration_can_drop_if_donor_goes_to_zero_or_from_equal_to_unequal():
    # equal -> unequal increases HHI (concentration drops)
    conc_equal = bf._compute_concentration({"a": 2, "b": 2})   # 1 - (0.5^2+0.5^2) = 0.5
    conc_unequal = bf._compute_concentration({"a": 1, "b": 3}) # 1 - (0.25+0.75^2)=0.375
    assert conc_unequal <= conc_equal

    # donor -> zero increases concentration toward single-author (worst)
    conc_11 = bf._compute_concentration({"a": 1, "b": 1})      # 0.5
    conc_02 = bf._compute_concentration({"a": 0, "b": 2})      # 0.0
    assert conc_02 <= conc_11

@settings(max_examples=100)
@given(st.lists(st.integers(min_value=1, max_value=20), min_size=1, max_size=10))
def test_base_score_non_decreasing_when_adding_new_small_author_pre_cap(counts):
    # skip when already at/over the diversity cap (5 authors)
    assume(len(counts) < 5)
    base1 = _base_score_from_counts(counts)
    base2 = _base_score_from_counts(counts + [1])
    assert base2 + 1e-12 >= base1