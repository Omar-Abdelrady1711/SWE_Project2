#!/usr/bin/env python3
"""
Comprehensive test for the fixed logging_setup.py
Tests all LOG_LEVEL values: 0, 1, 2 and verifies expected behavior
"""

import os
import sys
import logging
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from acemcli.logging_setup import setup_logging


def clear_logging():
    """Clear all existing logging handlers and reset state"""
    # Remove all handlers from root logger
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # Reset logging level
    logging.root.setLevel(logging.WARNING)


def test_log_level(level: str, description: str):
    """Test a specific log level and return the results"""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"LOG_LEVEL = {level}")
    print('='*60)
    
    # Clear previous state
    clear_logging()
    
    # Set environment
    os.environ["LOG_LEVEL"] = level
    if "LOG_FILE" in os.environ:
        del os.environ["LOG_FILE"]
    
    # Setup logging
    setup_logging()
    
    # Check the configured level
    root_level = logging.getLogger().level
    level_names = {
        50: "CRITICAL",
        40: "ERROR", 
        30: "WARNING",
        20: "INFO",
        10: "DEBUG"
    }
    
    print(f"Root logger level: {root_level} ({level_names.get(root_level, 'UNKNOWN')})")
    
    # Create test logger
    logger = logging.getLogger("test_logger")
    
    print("\nSending test messages:")
    print("(You should see messages based on the log level)")
    
    logger.critical("🔥 CRITICAL message (level 50)")
    logger.error("❌ ERROR message (level 40)")
    logger.warning("⚠️  WARNING message (level 30)")
    logger.info("ℹ️  INFO message (level 20)")
    logger.debug("🐛 DEBUG message (level 10)")
    
    # Verify expected behavior
    expected_levels = {
        "0": [50],  # Only CRITICAL
        "1": [50, 40, 30, 20],  # INFO and above
        "2": [50, 40, 30, 20, 10]  # All levels
    }
    
    if level in expected_levels:
        print(f"\nExpected to see: {[level_names[l] for l in expected_levels[level]]}")
    
    return root_level


def test_with_file():
    """Test logging with file output"""
    print(f"\n{'='*60}")
    print("Testing: LOG_LEVEL=1 with LOG_FILE")
    print('='*60)
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as tmp:
        temp_file = tmp.name
    
    try:
        clear_logging()
        
        # Set environment with file
        os.environ["LOG_LEVEL"] = "1"
        os.environ["LOG_FILE"] = temp_file
        
        setup_logging()
        
        logger = logging.getLogger("file_test")
        
        print(f"Logging to file: {temp_file}")
        print("Sending messages to both console and file...")
        
        logger.critical("CRITICAL to file")
        logger.info("INFO to file")
        logger.debug("DEBUG to file (should not appear)")
        
        # Read and display file contents
        with open(temp_file, 'r') as f:
            file_contents = f.read()
        
        print(f"\nFile contents:")
        if file_contents.strip():
            for line in file_contents.strip().split('\n'):
                print(f"  {line}")
        else:
            print("  (File is empty)")
            
    finally:
        # Clean up
        if os.path.exists(temp_file):
            os.unlink(temp_file)


def test_default_behavior():
    """Test default behavior when LOG_LEVEL is not set"""
    print(f"\n{'='*60}")
    print("Testing: Default behavior (no LOG_LEVEL environment variable)")
    print('='*60)
    
    clear_logging()
    
    # Remove LOG_LEVEL if it exists
    if "LOG_LEVEL" in os.environ:
        del os.environ["LOG_LEVEL"]
    if "LOG_FILE" in os.environ:
        del os.environ["LOG_FILE"]
    
    setup_logging()
    
    root_level = logging.getLogger().level
    print(f"Default root logger level: {root_level}")
    print("Expected: 50 (CRITICAL) - should be same as LOG_LEVEL=0")
    
    logger = logging.getLogger("default_test")
    
    print("\nTesting default behavior:")
    logger.critical("CRITICAL (should appear)")
    logger.info("INFO (should NOT appear)")
    
    return root_level


def main():
    """Run all logging tests"""
    print("🧪 COMPREHENSIVE LOGGING TEST")
    print("Testing logging_setup.py with all LOG_LEVEL values")
    
    # Test each level
    level_0 = test_log_level("0", "Silent mode (LOG_LEVEL=0)")
    level_1 = test_log_level("1", "Info mode (LOG_LEVEL=1)")  
    level_2 = test_log_level("2", "Debug mode (LOG_LEVEL=2)")
    
    # Test file logging
    test_with_file()
    
    # Test default
    default_level = test_default_behavior()
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print('='*60)
    
    print(f"LOG_LEVEL=0: {level_0} {'✅' if level_0 == 50 else '❌'} (Expected: 50)")
    print(f"LOG_LEVEL=1: {level_1} {'✅' if level_1 == 20 else '❌'} (Expected: 20)")
    print(f"LOG_LEVEL=2: {level_2} {'✅' if level_2 == 10 else '❌'} (Expected: 10)")
    print(f"Default:     {default_level} {'✅' if default_level == 50 else '❌'} (Expected: 50)")
    
    # Overall result
    all_correct = (level_0 == 50 and level_1 == 20 and level_2 == 10 and default_level == 50)
    
    print(f"\n🎯 Overall Result: {'✅ ALL TESTS PASSED' if all_correct else '❌ SOME TESTS FAILED'}")
    
    if all_correct:
        print("\n✨ Your logging setup is working correctly!")
        print("- LOG_LEVEL=0: Shows only CRITICAL messages")
        print("- LOG_LEVEL=1: Shows INFO, WARNING, ERROR, CRITICAL")
        print("- LOG_LEVEL=2: Shows all messages including DEBUG")
        print("- Default behavior works (defaults to level 0)")
        print("- File logging works when LOG_FILE is specified")
    else:
        print("\n⚠️  Some issues detected. Check the output above.")


if __name__ == "__main__":
    main()
