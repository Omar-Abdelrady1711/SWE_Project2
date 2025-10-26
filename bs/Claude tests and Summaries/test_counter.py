#!/usr/bin/env python3
"""
Quick test counter to verify our test suite progress.
"""

import subprocess
import sys
import os

def main():
    # Change to project directory
    project_dir = "/Users/blas/Documents/Obsidian Vault/School/F25/ECE 461/Project Repo/ECE30861_HW1"
    os.chdir(project_dir)
    
    print("🧪 ACME CLI Test Suite Status Report")
    print("=" * 50)
    
    try:
        # Run pytest to collect tests
        result = subprocess.run([
            sys.executable, '-m', 'pytest', '--collect-only', '-q'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            test_lines = [line for line in lines if 'test session starts' not in line and line.strip()]
            
            # Count test files and functions
            test_count = 0
            test_files = set()
            
            for line in test_lines:
                if '::test_' in line:
                    test_count += 1
                    file_part = line.split('::')[0]
                    if file_part.startswith('test/'):
                        test_files.add(file_part)
            
            print(f"📊 Total Test Cases: {test_count}")
            print(f"📁 Test Files: {len(test_files)}")
            print(f"🎯 Target for Week 2/3: 10-12 tests")
            print(f"🏆 Target for Phase 1: 20+ tests")
            
            if test_count >= 10:
                print("✅ MILESTONE ACHIEVED: 10+ tests for Week 2/3!")
            else:
                print(f"⚠️  Need {10 - test_count} more tests for milestone")
            
            print("\n📋 Test Files Found:")
            for test_file in sorted(test_files):
                print(f"  - {test_file}")
                
        else:
            print("❌ Error collecting tests:")
            print(result.stderr)
            
    except Exception as e:
        print(f"❌ Error running test collection: {e}")
    
    print("\n" + "=" * 50)
    print("🚀 Next Steps:")
    print("1. Run: ./run test")
    print("2. Check coverage percentage")
    print("3. Add more tests if needed")

if __name__ == "__main__":
    main()
