#!/usr/bin/env python3
"""
Simple test runner to check if pytest works without coverage
"""
import subprocess
import sys
import os

def main():
    project_dir = "/Users/blas/Documents/Obsidian Vault/School/F25/ECE 461/Project Repo/ECE30861_HW1"
    os.chdir(project_dir)
    
    print("Testing with basic pytest first...")
    print("=" * 50)
    
    try:
        # Run basic pytest
        result = subprocess.run([sys.executable, '-m', 'pytest', '-v'], 
                              capture_output=True, 
                              text=True, 
                              timeout=60)
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("\nSTDERR:")
            print(result.stderr)
        
        print(f"\nReturn code: {result.returncode}")
        
        # Count tests
        lines = result.stdout.split('\n')
        passed_tests = [line for line in lines if '::test_' in line and 'PASSED' in line]
        failed_tests = [line for line in lines if '::test_' in line and 'FAILED' in line]
        
        print(f"\nTest Summary:")
        print(f"✅ Passed: {len(passed_tests)}")
        print(f"❌ Failed: {len(failed_tests)}")
        print(f"📊 Total: {len(passed_tests) + len(failed_tests)}")
        
        if len(failed_tests) > 0:
            print(f"\nFailed tests:")
            for test in failed_tests:
                print(f"  - {test}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
