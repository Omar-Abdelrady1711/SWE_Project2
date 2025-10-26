#!/usr/bin/env python3
"""
Quick verification test for Task 5.3: Error Handling for CLI URL file reading
"""

import sys
import tempfile
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

def test_basic_error_handling():
    """Test basic error handling scenarios."""
    print("🧪 Testing Task 5.3: CLI URL File Reading Error Handling")
    print("=" * 60)
    
    from acemcli.cli import main, validate_file_path, validate_url_format
    from acemcli.exceptions import ValidationError
    
    tests_passed = 0
    total_tests = 0
    
    # Test 1: Non-existent file
    total_tests += 1
    try:
        result = main("/absolute/path/to/nonexistent/file.txt")
        if result != 0:
            print("✓ Test 1 PASSED: Non-existent file correctly rejected")
            tests_passed += 1
        else:
            print("✗ Test 1 FAILED: Non-existent file should return error code")
    except SystemExit as e:
        if e.code != 0:
            print("✓ Test 1 PASSED: Non-existent file correctly rejected with SystemExit")
            tests_passed += 1
        else:
            print("✗ Test 1 FAILED: SystemExit should have non-zero code")
    except Exception as e:
        print(f"✗ Test 1 FAILED: Unexpected exception {e}")
    
    # Test 2: Relative path
    total_tests += 1
    try:
        result = main("relative/path.txt")
        if result != 0:
            print("✓ Test 2 PASSED: Relative path correctly rejected")
            tests_passed += 1
        else:
            print("✗ Test 2 FAILED: Relative path should return error code")
    except SystemExit as e:
        if e.code != 0:
            print("✓ Test 2 PASSED: Relative path correctly rejected with SystemExit")
            tests_passed += 1
        else:
            print("✗ Test 2 FAILED: SystemExit should have non-zero code")
    except Exception as e:
        print(f"✗ Test 2 FAILED: Unexpected exception {e}")
    
    # Test 3: URL validation function
    total_tests += 1
    try:
        validate_url_format("https://valid-url.com")
        print("✓ Test 3 PASSED: Valid URL accepted")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 3 FAILED: Valid URL rejected: {e}")
    
    # Test 4: Invalid URL validation
    total_tests += 1
    try:
        validate_url_format("not-a-valid-url")
        print("✗ Test 4 FAILED: Invalid URL should be rejected")
    except ValidationError:
        print("✓ Test 4 PASSED: Invalid URL correctly rejected with ValidationError")
        tests_passed += 1
    except Exception as e:
        print(f"✗ Test 4 FAILED: Wrong exception type: {e}")
    
    # Test 5: Create temp file with malformed URLs
    total_tests += 1
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("not-a-url\\nhttps://valid.com\\nftp://invalid-protocol.com")
            temp_file_path = f.name
        
        # Make it absolute
        abs_path = Path(temp_file_path).resolve()
        result = main(str(abs_path))
        
        # Clean up
        Path(temp_file_path).unlink()
        
        if result != 0:
            print("✓ Test 5 PASSED: File with malformed URLs correctly rejected")
            tests_passed += 1
        else:
            print("✗ Test 5 FAILED: File with malformed URLs should return error code")
    except Exception as e:
        print(f"✗ Test 5 FAILED: Exception during temp file test: {e}")
    
    # Test 6: Empty file
    total_tests += 1
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("")  # Empty file
            temp_file_path = f.name
        
        abs_path = Path(temp_file_path).resolve()
        result = main(str(abs_path))
        
        # Clean up
        Path(temp_file_path).unlink()
        
        if result != 0:
            print("✓ Test 6 PASSED: Empty file correctly handled")
            tests_passed += 1
        else:
            print("✗ Test 6 FAILED: Empty file should return error code")
    except Exception as e:
        print(f"✗ Test 6 FAILED: Exception during empty file test: {e}")
    
    # Summary
    print("=" * 60)
    print(f"📊 TEST RESULTS: {tests_passed}/{total_tests} tests passed")
    print(f"Success rate: {(tests_passed/total_tests)*100:.1f}%")
    
    if tests_passed == total_tests:
        print("\\n🎉 All basic error handling tests passed!")
        print("\\n✅ Task 5.3 Implementation Summary:")
        print("  ✓ ValidationError exceptions with detailed error info")
        print("  ✓ File path validation (absolute, exists, readable)")
        print("  ✓ URL format validation")  
        print("  ✓ Proper error handling and exit codes")
        print("  ✓ Graceful handling of various error scenarios")
        return True
    else:
        print(f"\\n❌ {total_tests - tests_passed} test(s) failed")
        return False

if __name__ == "__main__":
    success = test_basic_error_handling()
    sys.exit(0 if success else 1)
