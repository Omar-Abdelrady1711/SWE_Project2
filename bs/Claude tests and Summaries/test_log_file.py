#!/usr/bin/env python3
"""
Simple test script to verify LOG_FILE environment variable functionality.
This is for ECE 461 Project - Task 1.2 by Blas.
"""

import os
import sys
import tempfile
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from acemcli.logging_setup import setup_logging


def test_log_file_functionality():
    """Test that LOG_FILE environment variable works correctly."""
    print("=== LOG_FILE ENVIRONMENT VARIABLE TEST ===")
    
    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as temp_file:
        temp_log_path = temp_file.name
    
    try:
        print(f"Using temporary log file: {temp_log_path}")
        
        # Set environment variables
        os.environ["LOG_LEVEL"] = "1"  # INFO level
        os.environ["LOG_FILE"] = temp_log_path
        
        # Clear any existing handlers
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        
        # Setup logging with file
        setup_logging()
        
        # Create a test logger
        logger = logging.getLogger("file_test")
        
        # Log some test messages
        test_messages = [
            ("CRITICAL", "This is a critical message for file test"),
            ("ERROR", "This is an error message for file test"),
            ("WARNING", "This is a warning message for file test"),
            ("INFO", "This is an info message for file test"),
        ]
        
        print("\nSending test messages to log file...")
        for level, message in test_messages:
            getattr(logger, level.lower())(message)
            print(f"  Sent {level}: {message}")
        
        # Force flush
        for handler in logging.root.handlers:
            handler.flush()
        
        # Read back the log file
        print(f"\nReading back log file contents:")
        log_path = Path(temp_log_path)
        if log_path.exists():
            content = log_path.read_text(encoding='utf-8')
            if content.strip():
                print("Log file contents:")
                for i, line in enumerate(content.strip().split('\n'), 1):
                    print(f"  {i}: {line}")
                
                # Verify all messages are present
                missing_messages = []
                for level, message in test_messages:
                    if message not in content:
                        missing_messages.append(f"{level}: {message}")
                
                if missing_messages:
                    print(f"\n❌ FAIL: Missing messages in log file:")
                    for msg in missing_messages:
                        print(f"    - {msg}")
                    return False
                else:
                    print(f"\n✅ PASS: All {len(test_messages)} messages found in log file!")
                    return True
            else:
                print("❌ FAIL: Log file is empty!")
                return False
        else:
            print("❌ FAIL: Log file was not created!")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Exception occurred: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Clean up
        try:
            os.unlink(temp_log_path)
            print(f"\nCleaned up temporary file: {temp_log_path}")
        except:
            pass
        
        # Clear environment variables
        if "LOG_FILE" in os.environ:
            del os.environ["LOG_FILE"]
        if "LOG_LEVEL" in os.environ:
            del os.environ["LOG_LEVEL"]


def test_no_log_file():
    """Test that logging works without LOG_FILE (console only)."""
    print("\n=== TESTING WITHOUT LOG_FILE ===")
    
    # Clear environment variables
    if "LOG_FILE" in os.environ:
        del os.environ["LOG_FILE"]
    os.environ["LOG_LEVEL"] = "1"
    
    # Clear handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    setup_logging()
    
    logger = logging.getLogger("console_test")
    print("The following messages should appear on console:")
    logger.info("This is a console-only log message")
    logger.warning("This is a warning that should appear")
    
    print("✅ Console logging test completed")
    return True


def main():
    """Run all log file tests."""
    print("LOG_FILE Environment Variable Verification")
    print("=" * 50)
    
    success = True
    
    # Test 1: LOG_FILE functionality
    success &= test_log_file_functionality()
    
    # Test 2: Console-only (no LOG_FILE)
    success &= test_no_log_file()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 ALL TESTS PASSED! LOG_FILE functionality is working correctly.")
    else:
        print("💥 SOME TESTS FAILED! Check the output above for details.")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
