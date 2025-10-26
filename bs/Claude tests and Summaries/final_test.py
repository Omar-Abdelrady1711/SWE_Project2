#!/usr/bin/env python3
"""
Final test run after all fixes
"""
import subprocess
import sys
import os
from pathlib import Path

def main():
    project_dir = "/Users/blas/Documents/Obsidian Vault/School/F25/ECE 461/Project Repo/ECE30861_HW1"
    os.chdir(project_dir)
    
    output_file = Path("final_test_results.txt")
    
    with open(output_file, "w") as f:
        f.write("🎯 FINAL TEST RESULTS\n")
        f.write("=" * 40 + "\n\n")
        
        # Check all components
        checks = []
        
        # 1. Run file
        run_file = Path("./run")
        checks.append(("Run file executable", os.access(run_file, os.X_OK)))
        
        # 2. Pytest
        try:
            result = subprocess.run([sys.executable, '-m', 'pytest', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            checks.append(("Pytest available", result.returncode == 0))
        except:
            checks.append(("Pytest available", False))
        
        # 3. Module imports
        try:
            from acemcli.logging_setup import setup_logging
            checks.append(("acemcli.logging_setup", True))
        except:
            checks.append(("acemcli.logging_setup", False))
            
        try:
            from acemcli.metrics.performance_claims import PerformanceClaimsMetric
            checks.append(("performance_claims metric", True))
        except:
            checks.append(("performance_claims metric", False))
            
        try:
            from acemcli.cli import infer_category
            checks.append(("acemcli.cli", True))
        except:
            checks.append(("acemcli.cli", False))
        
        # Print check results
        for check_name, status in checks:
            symbol = "✅" if status else "❌"
            f.write(f"{symbol} {check_name}: {status}\n")
        
        all_good = all(status for _, status in checks)
        f.write(f"\n{'🎉 ALL SYSTEMS GO!' if all_good else '⚠️ Some issues remain'}\n")
        
        if all_good:
            f.write("\n🧪 RUNNING ACTUAL TESTS...\n")
            f.write("-" * 40 + "\n")
            
            # Try ./run test
            try:
                result = subprocess.run(['./run', 'test'], 
                                      capture_output=True, text=True, timeout=120)
                f.write(f"Return code: {result.returncode}\n")
                f.write(f"STDOUT:\n{result.stdout}\n")
                if result.stderr:
                    f.write(f"STDERR:\n{result.stderr}\n")
                    
                # Extract test count
                if "test cases passed" in result.stdout:
                    lines = result.stdout.split('\n')
                    summary_line = [line for line in lines if "test cases passed" in line]
                    if summary_line:
                        f.write(f"\n🏆 RESULT: {summary_line[-1]}\n")
                        
            except Exception as e:
                f.write(f"Test run error: {e}\n")
    
    print(f"Final results written to {output_file}")

if __name__ == "__main__":
    main()
