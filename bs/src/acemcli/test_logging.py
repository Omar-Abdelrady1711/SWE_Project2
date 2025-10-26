#!/usr/bin/env python3
"""
Test script for logging_setup.py
Tests all LOG_LEVEL values: 0 (silent), 1 (info), 2 (debug)
"""

import os
import sys
import tempfile
import logging
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from acemcli.logging_setup import setup_logging


def test_logging_level(log_level: str, log_file: str = None, test_name: str = ""):
    """Test logging setup with specific log level and optional log file"""
    print(f"\n{'='*60}")
    print(f"Testing {test_name}")
    print(f"LOG_LEVEL={log_level}, LOG_FILE={log_file}")
    print('='*60)
    
    # Set environment variables
    os.environ["LOG_LEVEL"] = log_level
    if log_file:
        os.environ["LOG_FILE"] = log_file
    elif "LOG_FILE" in os.environ:
        del os.environ["LOG_FILE"]
    
    # Clear any existing handlers to start fresh
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # Setup logging
    setup_logging()
    
    # Get a logger to test with
    logger = logging.getLogger("test_logger")
    
    print(f"Current logging level: {logging.getLogger().level}")
    print(f"Level names: CRITICAL={logging.CRITICAL}, ERROR={logging.ERROR}, WARNING={logging.WARNING}, INFO={logging.INFO}, DEBUG={logging.DEBUG}")
    
    # Test different log levels
    print("\nTesting log messages:")
    logger.critical("🔥 CRITICAL message - should always appear")
    logger.error("❌ ERROR message")
    logger.warning("⚠️  WARNING message") 
    logger.info("ℹ️  INFO message")
    logger.debug("🐛 DEBUG message")
    
    # If log file was specified, show file contents
    if log_file and os.path.exists(log_file):
        print(f"\nLog file contents ({log_file}):")
        with open(log_file, 'r') as f:
            content = f.read()
            if content.strip():
                print(content)
            else:
                print("(Log file is empty)")


def main():
    print("Testing logging_setup.py with all LOG_LEVEL values")
    print("Expected behavior:")
    print("- LOG_LEVEL=0: Only CRITICAL messages (silent mode)")
    print("- LOG_LEVEL=1: INFO, WARNING, ERROR, CRITICAL messages")
    print("- LOG_LEVEL=2: DEBUG, INFO, WARNING, ERROR, CRITICAL messages")
    
    # Create temporary log file for testing
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as tmp_file:
        temp_log_file = tmp_file.name
    
    try:
        # Test 1: LOG_LEVEL=0 (silent/critical only) - console only
        test_logging_level("0", None, "LOG_LEVEL=0 (Silent - Critical Only) - Console")
        
        # Test 2: LOG_LEVEL=1 (info level) - console only  
        test_logging_level("1", None, "LOG_LEVEL=1 (Info Level) - Console")
        
        # Test 3: LOG_LEVEL=2 (debug level) - console only
        test_logging_level("2", None, "LOG_LEVEL=2 (Debug Level) - Console")
        
        # Test 4: LOG_LEVEL=0 with log file
        test_logging_level("0", temp_log_file, "LOG_LEVEL=0 (Silent) - With Log File")
        
        # Test 5: LOG_LEVEL=1 with log file
        test_logging_level("1", temp_log_file, "LOG_LEVEL=1 (Info) - With Log File")
        
        # Test 6: LOG_LEVEL=2 with log file
        test_logging_level("2", temp_log_file, "LOG_LEVEL=2 (Debug) - With Log File")
        
        # Test 7: No LOG_LEVEL set (should default to 0)
        if "LOG_LEVEL" in os.environ:
            del os.environ["LOG_LEVEL"]
        test_logging_level("", None, "No LOG_LEVEL set (Should default to 0)")
        
        print(f"\n{'='*60}")
        print("✅ All logging tests completed!")
        print("Review the output above to verify:")
        print("1. LOG_LEVEL=0 shows only CRITICAL messages")
        print("2. LOG_LEVEL=1 shows INFO, WARNING, ERROR, CRITICAL")  
        print("3. LOG_LEVEL=2 shows all messages including DEBUG")
        print("4. Log file functionality works when LOG_FILE is set")
        print("5. Default behavior (no LOG_LEVEL) works correctly")
        
    finally:
        # Clean up temp file
        if os.path.exists(temp_log_file):
            os.unlink(temp_log_file)


if __name__ == "__main__":
    main()
