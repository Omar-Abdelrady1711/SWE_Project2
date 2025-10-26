#!/usr/bin/env python3
"""
Minimal test to check if basic imports work.
"""

def test_simple():
    """A simple test that should always pass."""
    assert 1 + 1 == 2

def test_import_logging():
    """Test if we can import the logging module."""
    try:
        from acemcli.logging_setup import setup_logging
        assert True  # Import worked
    except ImportError as e:
        print(f"Import failed: {e}")
        assert False, f"Cannot import logging_setup: {e}"

if __name__ == "__main__":
    test_simple()
    test_import_logging()
    print("✅ Basic tests passed!")
