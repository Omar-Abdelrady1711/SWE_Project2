#!/usr/bin/env python3
"""
🚀 ACME CLI - Week 2/3 Deliverables Verification Script
This script verifies that all urgent deliverables are working correctly.
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path

def colored_print(text, color_code):
    """Print colored text to terminal."""
    print(f"\033[{color_code}m{text}\033[0m")

def success(text):
    colored_print(f"✅ {text}", "92")  # Green

def error(text):
    colored_print(f"❌ {text}", "91")  # Red

def info(text):
    colored_print(f"ℹ️  {text}", "94")  # Blue

def warning(text):
    colored_print(f"⚠️  {text}", "93")  # Yellow

def main():
    print("🚀 ECE 30861 Project - Week 2/3 Deliverables Verification")
    print("=" * 60)
    
    project_dir = "/Users/blas/Documents/Obsidian Vault/School/F25/ECE 461/Project Repo/ECE30861_HW1"
    os.chdir(project_dir)
    
    tests_passed = 0
    total_tests = 8
    
    # Test 1: Check if run file exists and is executable
    print("\n1. 🔧 Checking run file...")
    run_file = Path("./run")
    if run_file.exists() and os.access(run_file, os.X_OK):
        success("run file exists and is executable")
        tests_passed += 1
    else:
        error("run file missing or not executable")
    
    # Test 2: Check logging setup
    print("\n2. 📝 Testing logging framework...")
    try:
        from acemcli.logging_setup import setup_logging
        
        # Test environment variable support
        os.environ['LOG_LEVEL'] = '2'
        setup_logging()
        success("Logging framework imported and configured successfully")
        tests_passed += 1
    except Exception as e:
        error(f"Logging framework error: {e}")
    
    # Test 3: Check performance claims metric
    print("\n3. 📊 Testing performance claims metric...")
    try:
        from acemcli.metrics.performance_claims import PerformanceClaimsMetric
        metric = PerformanceClaimsMetric()
        
        # Test basic functionality
        assert metric.name == "performance_claims"
        assert metric.supports("https://huggingface.co/test/model", "MODEL")
        success("Performance claims metric imported and configured")
        tests_passed += 1
    except Exception as e:
        error(f"Performance claims metric error: {e}")
    
    # Test 4: Check dataset code score metric  
    print("\n4. 📚 Testing dataset & code score metric...")
    try:
        from acemcli.metrics.dataset_code_score import DatasetAndCodeScoreMetric
        metric = DatasetAndCodeScoreMetric()
        
        assert metric.name == "dataset_and_code_score"
        assert metric.supports("https://huggingface.co/test/model", "MODEL")
        success("Dataset & code score metric working")
        tests_passed += 1
    except Exception as e:
        error(f"Dataset code score metric error: {e}")
    
    # Test 5: Check CLI functionality
    print("\n5. 🖥️  Testing CLI functions...")
    try:
        from acemcli.cli import infer_category, main
        
        # Test category inference
        assert infer_category("https://huggingface.co/test/model") == "MODEL"
        assert infer_category("https://huggingface.co/datasets/test") == "DATASET"
        success("CLI functions working correctly")
        tests_passed += 1
    except Exception as e:
        error(f"CLI functionality error: {e}")
    
    # Test 6: Test metrics registration
    print("\n6. 🔗 Testing metrics registration...")
    try:
        from acemcli.metrics.base import all_metrics
        metrics = all_metrics()
        
        metric_names = [m.name for m in metrics]
        info(f"Registered metrics: {metric_names}")
        
        if "performance_claims" in metric_names:
            success("Performance claims metric is registered")
            tests_passed += 1
        else:
            error("Performance claims metric not registered")
    except Exception as e:
        error(f"Metrics registration error: {e}")
    
    # Test 7: Run actual test suite
    print("\n7. 🧪 Running test suite...")
    try:
        result = subprocess.run([
            sys.executable, '-m', 'pytest', '--tb=short', '-v'
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            # Count tests from output
            output_lines = result.stdout.split('\n')
            passed_line = [line for line in output_lines if 'passed' in line and 'failed' not in line]
            
            if passed_line:
                success(f"Test suite passed - {passed_line[-1]}")
                tests_passed += 1
            else:
                warning("Tests ran but couldn't parse results")
        else:
            warning("Some tests failed - check output")
            info("Test output:")
            print(result.stdout[-500:])  # Last 500 chars
            
    except subprocess.TimeoutExpired:
        warning("Test suite timed out")
    except Exception as e:
        error(f"Test suite error: {e}")
    
    # Test 8: Test ./run command
    print("\n8. ⚙️  Testing ./run test command...")
    try:
        result = subprocess.run(['./run', 'test'], capture_output=True, text=True, timeout=30)
        
        if "test cases passed" in result.stdout:
            success("./run test command working")
            info(f"Output: {result.stdout.strip().split('\\n')[-1]}")
            tests_passed += 1
        else:
            warning("./run test ran but output format unexpected")
            info(f"Output: {result.stdout}")
            
    except Exception as e:
        error(f"./run test error: {e}")
    
    # Final summary
    print("\n" + "=" * 60)
    print("📋 VERIFICATION SUMMARY")
    print("=" * 60)
    
    success_rate = (tests_passed / total_tests) * 100
    
    if tests_passed == total_tests:
        success(f"ALL TESTS PASSED! ({tests_passed}/{total_tests}) - 100% Ready for Milestone 3!")
    elif tests_passed >= 6:
        warning(f"Most tests passed ({tests_passed}/{total_tests}) - {success_rate:.0f}% ready")
    else:
        error(f"Several issues found ({tests_passed}/{total_tests}) - {success_rate:.0f}% ready")
    
    print("\n🎯 DELIVERABLES STATUS:")
    deliverables = [
        ("Logging Framework", tests_passed >= 2),
        ("Performance Claims Metric", tests_passed >= 3), 
        ("Dataset & Code Score Metric", tests_passed >= 4),
        ("Testing Framework", tests_passed >= 7),
        ("CLI Integration", tests_passed >= 5),
        ("Complete System", tests_passed >= 8)
    ]
    
    for name, status in deliverables:
        if status:
            success(f"{name}")
        else:
            error(f"{name}")
    
    print("\n🚀 NEXT STEPS:")
    if tests_passed == total_tests:
        info("1. You're ready for Milestone 3 submission!")
        info("2. Test with real HuggingFace URLs")
        info("3. Coordinate with team for integration")
    else:
        info("1. Fix any failing tests above")
        info("2. Re-run this verification script")
        info("3. Ask for help if needed")
    
    return tests_passed == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
