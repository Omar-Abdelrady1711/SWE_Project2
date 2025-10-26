#!/usr/bin/env python3
"""
Comprehensive diagnostic script that writes results to a file
"""
import subprocess
import sys
import os
import traceback
from pathlib import Path

def main():
    project_dir = "/Users/blas/Documents/Obsidian Vault/School/F25/ECE 461/Project Repo/ECE30861_HW1"
    os.chdir(project_dir)
    
    output_file = Path("test_diagnostic_output.txt")
    
    with open(output_file, "w") as f:
        f.write("🚀 ACME CLI Test Diagnostic Report\n")
        f.write("=" * 50 + "\n\n")
        
        # Test 1: Check current directory
        f.write(f"1. Current directory: {os.getcwd()}\n")
        
        # Test 2: Check if run file exists
        run_file = Path("./run")
        f.write(f"2. Run file exists: {run_file.exists()}\n")
        f.write(f"   Run file executable: {os.access(run_file, os.X_OK)}\n\n")
        
        # Test 3: Try basic pytest
        f.write("3. Testing basic pytest...\n")
        try:
            result = subprocess.run([sys.executable, '-m', 'pytest', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            f.write(f"   Pytest available: {result.returncode == 0}\n")
            f.write(f"   Pytest version: {result.stdout.strip()}\n")
        except Exception as e:
            f.write(f"   Pytest error: {e}\n")
        
        # Test 4: Check if we can import our modules
        f.write("\n4. Testing imports...\n")
        try:
            from acemcli.logging_setup import setup_logging
            f.write("   ✅ acemcli.logging_setup imported successfully\n")
        except Exception as e:
            f.write(f"   ❌ acemcli.logging_setup import failed: {e}\n")
        
        try:
            from acemcli.metrics.performance_claims import PerformanceClaimsMetric
            f.write("   ✅ performance_claims metric imported successfully\n")
        except Exception as e:
            f.write(f"   ❌ performance_claims metric import failed: {e}\n")
            f.write(f"   Traceback: {traceback.format_exc()}\n")
        
        try:
            from acemcli.cli import infer_category
            f.write("   ✅ acemcli.cli imported successfully\n")
        except Exception as e:
            f.write(f"   ❌ acemcli.cli import failed: {e}\n")
        
        # Test 5: Try to collect tests
        f.write("\n5. Testing pytest collection...\n")
        try:
            result = subprocess.run([sys.executable, '-m', 'pytest', '--collect-only', '-q'], 
                                  capture_output=True, text=True, timeout=30)
            f.write(f"   Collection return code: {result.returncode}\n")
            f.write(f"   STDOUT:\n{result.stdout}\n")
            if result.stderr:
                f.write(f"   STDERR:\n{result.stderr}\n")
                
            # Count collected tests
            lines = result.stdout.split('\n')
            test_lines = [line for line in lines if '::test_' in line]
            f.write(f"   Tests found: {len(test_lines)}\n")
            
        except Exception as e:
            f.write(f"   Collection error: {e}\n")
        
        # Test 6: Try running actual tests (if collection worked)
        f.write("\n6. Testing actual test run...\n")
        try:
            result = subprocess.run([sys.executable, '-m', 'pytest', '-v', '--tb=short'], 
                                  capture_output=True, text=True, timeout=60)
            f.write(f"   Test run return code: {result.returncode}\n")
            f.write(f"   STDOUT:\n{result.stdout}\n")
            if result.stderr:
                f.write(f"   STDERR:\n{result.stderr}\n")
                
        except Exception as e:
            f.write(f"   Test run error: {e}\n")
        
        # Test 7: Try the ./run test command
        f.write("\n7. Testing ./run test command...\n")
        try:
            result = subprocess.run(['./run', 'test'], 
                                  capture_output=True, text=True, timeout=60)
            f.write(f"   ./run test return code: {result.returncode}\n")
            f.write(f"   STDOUT:\n{result.stdout}\n")
            if result.stderr:
                f.write(f"   STDERR:\n{result.stderr}\n")
                
        except Exception as e:
            f.write(f"   ./run test error: {e}\n")
        
        f.write("\n" + "=" * 50 + "\n")
        f.write("Diagnostic complete! Check this file for results.\n")
    
    print(f"Diagnostic complete! Results written to {output_file}")

if __name__ == "__main__":
    main()
