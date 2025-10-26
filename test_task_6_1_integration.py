#!/usr/bin/env python3
"""
Task 6.1: Integration Test - Test with full ./run URL_FILE command

This script tests the complete end-to-end flow of the ACME CLI tool.

Test Requirements:
1. Create test URL file with 3 different URL types (MODEL, DATASET, CODE)
2. Run ./run URL_FILE command
3. Verify NDJSON output format
4. Check latency measurements are positive integers
5. Verify all required fields are present

Expected Behavior:
- MODEL URLs should be processed and produce NDJSON output
- DATASET and CODE URLs should be skipped (only MODEL category processed)
- Each output line should be valid NDJSON with all required fields
- All latency values should be non-negative integers
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List

# Define paths
REPO_ROOT = Path(__file__).parent.parent
BS_DIR = REPO_ROOT / "bs"
RUN_SCRIPT = BS_DIR / "run"
TEST_URL_FILE = BS_DIR / "test_urls_task_6_1.txt"

# Required fields in NDJSON output
REQUIRED_FIELDS = [
    "name",
    "category",
    "net_score",
    "net_score_latency",
    "ramp_up_time",
    "ramp_up_time_latency",
    "bus_factor",
    "bus_factor_latency",
    "performance_claims",
    "performance_claims_latency",
    "license",
    "license_latency",
    "size_score",
    "size_score_latency",
    "dataset_and_code_score",
    "dataset_and_code_score_latency",
    "dataset_quality",
    "dataset_quality_latency",
    "code_quality",
    "code_quality_latency",
]

def print_header(title: str):
    """Print formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_success(msg: str):
    """Print success message"""
    print(f"✅ {msg}")

def print_error(msg: str):
    """Print error message"""
    print(f"❌ {msg}")

def print_info(msg: str):
    """Print info message"""
    print(f"ℹ️  {msg}")

def create_test_url_file() -> Path:
    """Create a test URL file with 3 different URL types"""
    print_header("STEP 1: Creating Test URL File")
    
    content = """# Test URL File for Task 6.1 - Integration Testing
# This file contains 3 different URL types as specified in the requirements

# MODEL URL (should be processed)
https://huggingface.co/bert-base-uncased

# DATASET URL (should be skipped - not MODEL category)
https://huggingface.co/datasets/squad

# CODE URL (should be skipped - not MODEL category)
https://github.com/huggingface/transformers
"""
    
    TEST_URL_FILE.write_text(content)
    print_success(f"Created test URL file: {TEST_URL_FILE}")
    print_info(f"File contains 3 URLs: 1 MODEL, 1 DATASET, 1 CODE")
    print_info(f"Expected: Only MODEL URL should be processed")
    
    return TEST_URL_FILE

def verify_run_script_exists() -> bool:
    """Verify that the ./run script exists and is executable"""
    print_header("STEP 2: Verifying ./run Script")
    
    if not RUN_SCRIPT.exists():
        print_error(f"./run script not found at: {RUN_SCRIPT}")
        return False
    
    print_success(f"Found ./run script at: {RUN_SCRIPT}")
    
    # Check if executable
    if not os.access(RUN_SCRIPT, os.X_OK):
        print_info("Making ./run script executable...")
        RUN_SCRIPT.chmod(0o755)
        print_success("./run script is now executable")
    else:
        print_success("./run script is executable")
    
    return True

def run_cli_command(url_file: Path) -> tuple[int, str, str]:
    """Run the ./run URL_FILE command"""
    print_header("STEP 3: Running ./run URL_FILE Command")
    
    # Convert to absolute path as required by the CLI
    absolute_path = url_file.absolute()
    print_info(f"Running command: {RUN_SCRIPT} {absolute_path}")
    
    # Set environment variables for logging
    env = os.environ.copy()
    env['LOG_LEVEL'] = '1'  # Info level
    env['LOG_FILE'] = str(BS_DIR / 'integration_test.log')
    
    print_info(f"LOG_LEVEL=1 (info)")
    print_info(f"LOG_FILE={env['LOG_FILE']}")
    
    try:
        result = subprocess.run(
            [str(RUN_SCRIPT), str(absolute_path)],
            cwd=BS_DIR,
            capture_output=True,
            text=True,
            env=env,
            timeout=60  # 60 second timeout
        )
        
        return result.returncode, result.stdout, result.stderr
    
    except subprocess.TimeoutExpired:
        print_error("Command timed out after 60 seconds")
        return -1, "", "Timeout"
    except Exception as e:
        print_error(f"Failed to run command: {e}")
        return -1, "", str(e)

def parse_ndjson_output(stdout: str) -> List[Dict[str, Any]]:
    """Parse NDJSON output into a list of dictionaries"""
    print_header("STEP 4: Parsing NDJSON Output")
    
    if not stdout.strip():
        print_error("No output received (stdout is empty)")
        return []
    
    lines = stdout.strip().split('\n')
    print_info(f"Received {len(lines)} output line(s)")
    
    results = []
    for i, line in enumerate(lines, 1):
        if not line.strip():
            continue
        
        try:
            data = json.loads(line)
            results.append(data)
            print_success(f"Line {i}: Valid JSON parsed")
        except json.JSONDecodeError as e:
            print_error(f"Line {i}: Invalid JSON - {e}")
            print_info(f"  Content: {line[:100]}...")
    
    return results

def verify_ndjson_format(results: List[Dict[str, Any]]) -> bool:
    """Verify NDJSON output format and required fields"""
    print_header("STEP 5: Verifying NDJSON Format")
    
    if not results:
        print_error("No results to verify")
        return False
    
    all_valid = True
    
    for i, result in enumerate(results, 1):
        print(f"\n📊 Result {i}: {result.get('name', 'UNKNOWN')}")
        print("-" * 60)
        
        # Check all required fields are present
        missing_fields = [f for f in REQUIRED_FIELDS if f not in result]
        if missing_fields:
            print_error(f"Missing fields: {', '.join(missing_fields)}")
            all_valid = False
        else:
            print_success("All required fields present")
        
        # Verify category is MODEL (since we filter to MODEL only)
        if result.get('category') != 'MODEL':
            print_error(f"Expected category='MODEL', got '{result.get('category')}'")
            all_valid = False
        else:
            print_success(f"Category: {result['category']}")
        
        # Verify scores are in [0, 1] range
        score_fields = [
            'net_score', 'ramp_up_time', 'bus_factor', 'performance_claims',
            'license', 'dataset_and_code_score', 'dataset_quality', 'code_quality'
        ]
        for field in score_fields:
            if field in result:
                value = result[field]
                if isinstance(value, (int, float)):
                    if 0 <= value <= 1:
                        print_success(f"{field}: {value:.3f} (valid range)")
                    else:
                        print_error(f"{field}: {value} (out of range [0,1])")
                        all_valid = False
        
        # Verify size_score structure
        if 'size_score' in result:
            size_score = result['size_score']
            if isinstance(size_score, dict):
                expected_keys = ['raspberry_pi', 'jetson_nano', 'desktop_pc', 'aws_server']
                for key in expected_keys:
                    if key in size_score:
                        value = size_score[key]
                        if isinstance(value, (int, float)) and 0 <= value <= 1:
                            print_success(f"size_score.{key}: {value:.3f}")
                        else:
                            print_error(f"size_score.{key}: {value} (invalid)")
                            all_valid = False
            else:
                print_error("size_score is not a dictionary")
                all_valid = False
    
    return all_valid

def verify_latency_measurements(results: List[Dict[str, Any]]) -> bool:
    """Verify all latency measurements are positive integers"""
    print_header("STEP 6: Verifying Latency Measurements")
    
    if not results:
        print_error("No results to verify")
        return False
    
    latency_fields = [
        'net_score_latency',
        'ramp_up_time_latency',
        'bus_factor_latency',
        'performance_claims_latency',
        'license_latency',
        'size_score_latency',
        'dataset_and_code_score_latency',
        'dataset_quality_latency',
        'code_quality_latency',
    ]
    
    all_valid = True
    
    for i, result in enumerate(results, 1):
        print(f"\n⏱️  Result {i}: {result.get('name', 'UNKNOWN')}")
        print("-" * 60)
        
        for field in latency_fields:
            if field in result:
                value = result[field]
                
                # Check if it's an integer
                if not isinstance(value, int):
                    print_error(f"{field}: {value} (not an integer)")
                    all_valid = False
                    continue
                
                # Check if it's non-negative
                if value < 0:
                    print_error(f"{field}: {value} (negative value)")
                    all_valid = False
                else:
                    print_success(f"{field}: {value} ms")
            else:
                print_error(f"{field}: MISSING")
                all_valid = False
    
    return all_valid

def main():
    """Main test execution"""
    print_header("TASK 6.1: INTEGRATION TEST - Full ./run URL_FILE Command")
    print_info("Testing the complete end-to-end CLI workflow")
    
    # Track test results
    tests_passed = 0
    tests_total = 6
    
    # Step 1: Create test URL file
    try:
        url_file = create_test_url_file()
        tests_passed += 1
    except Exception as e:
        print_error(f"Failed to create test URL file: {e}")
        return 1
    
    # Step 2: Verify ./run script exists
    if verify_run_script_exists():
        tests_passed += 1
    else:
        print_error("Cannot proceed without ./run script")
        return 1
    
    # Step 3: Run the CLI command
    returncode, stdout, stderr = run_cli_command(url_file)
    
    if returncode != 0:
        print_error(f"Command failed with return code: {returncode}")
        print_info("STDERR:")
        print(stderr)
        print_info("STDOUT:")
        print(stdout)
        # Don't fail completely, try to parse output anyway
    else:
        print_success(f"Command completed successfully (return code: {returncode})")
        tests_passed += 1
    
    if stderr:
        print_info("STDERR output:")
        print(stderr)
    
    # Step 4: Parse NDJSON output
    results = parse_ndjson_output(stdout)
    if results:
        tests_passed += 1
        print_success(f"Successfully parsed {len(results)} result(s)")
    else:
        print_error("Failed to parse any results")
        print_info("Raw stdout:")
        print(stdout)
        return 1
    
    # Step 5: Verify NDJSON format
    if verify_ndjson_format(results):
        tests_passed += 1
        print_success("NDJSON format verification passed")
    else:
        print_error("NDJSON format verification failed")
    
    # Step 6: Verify latency measurements
    if verify_latency_measurements(results):
        tests_passed += 1
        print_success("Latency measurement verification passed")
    else:
        print_error("Latency measurement verification failed")
    
    # Final Summary
    print_header("TASK 6.1 TEST SUMMARY")
    print(f"\n📊 Tests Passed: {tests_passed}/{tests_total}")
    
    if tests_passed == tests_total:
        print_success("✨ ALL TESTS PASSED! Task 6.1 is COMPLETE ✅")
        return 0
    else:
        print_error(f"❌ {tests_total - tests_passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
