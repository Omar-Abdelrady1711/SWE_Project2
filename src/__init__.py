"""Top-level package shim for tests that import `src.*`.

This file intentionally left minimal — presence makes `src` a real package
so both `src.metrics` and top-level `metrics` import styles can work
depending on how the test runner manipulates sys.path.
"""
__all__ = []
# ACME CLI package
