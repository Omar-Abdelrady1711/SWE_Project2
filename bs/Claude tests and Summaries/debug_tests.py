#!/usr/bin/env python3
"""
Debug script to see why tests aren't being found.
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    print("🔍 Debug: Why aren't tests being found?")
    print("=" * 50)
    
    # Check current directory
    print(f"Current directory: {os.getcwd()}")
    
    # Check if test directory exists
    test_dir = Path("test")
    print(f"Test directory exists: {test_dir.exists()}")
    
    if test_dir.exists():
        test_files = list(test_dir.glob("test_*.py"))
        print(f"Test files found: {len(test_files)}")
        for f in test_files:
            print(f"  - {f}")
    
    # Check if package can be imported
    try:
        import acmecli
        print("✅ acmecli package can be imported")
        print(f"Package location: {acmecli.__file__}")
    except ImportError as e:
        print(f"❌ Cannot import acmecli: {e}")
    
    # Check pytest version
    try:
        result = subprocess.run([sys.executable, '-m', 'pytest', '--version'], 
                              capture_output=True, text=True)
        print(f"Pytest version: {result.stdout.strip()}")
    except Exception as e:
        print(f"❌ Pytest error: {e}")
    
    # Try to collect tests
    print("\n🧪 Attempting to collect tests...")
    try:
        result = subprocess.run([sys.executable, '-m', 'pytest', '--collect-only'], 
                              capture_output=True, text=True)
        print("STDOUT:")
        print(result.stdout)
        print("STDERR:")
        print(result.stderr)
        print(f"Return code: {result.returncode}")
    except Exception as e:
        print(f"❌ Collection error: {e}")

if __name__ == "__main__":
    main()
