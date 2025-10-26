#!/usr/bin/env python3
"""
Logging test that writes results to file for verification
"""

import os
import sys
import logging
import tempfile
from pathlib import Path
from io import StringIO

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from acemcli.logging_setup import setup_logging

def test_logging_levels():
    results = []
    
    # Test each log level
    for level, level_name in [("0", "CRITICAL"), ("1", "INFO"), ("2", "DEBUG")]:
        results.append(f"\n{'='*50}")
        results.append(f"Testing LOG_LEVEL={level} ({level_name})")
        results.append('='*50)
        
        # Set environment
        os.environ["LOG_LEVEL"] = level
        if "LOG_FILE" in os.environ:
            del os.environ["LOG_FILE"]
        
        # Clear any existing handlers
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        
        # Capture log output to a string
        log_capture_string = StringIO()
        ch = logging.StreamHandler(log_capture_string)
        
        # Setup logging
        setup_logging()
        
        # Add our capture handler
        logging.getLogger().addHandler(ch)
        
        # Create logger and test messages
        logger = logging.getLogger(f"test_level_{level}")
        
        # Test all message types
        logger.critical("CRITICAL: This is a critical message")
        logger.error("ERROR: This is an error message")
        logger.warning("WARNING: This is a warning message")
        logger.info("INFO: This is an info message")
        logger.debug("DEBUG: This is a debug message")
        
        # Get captured output
        log_contents = log_capture_string.getvalue()
        
        # Analyze what was captured
        lines = log_contents.strip().split('\n') if log_contents.strip() else []
        
        results.append(f"Root logger level: {logging.getLogger().level}")
        results.append(f"Number of log messages captured: {len(lines)}")
        results.append("Captured messages:")
        if lines:
            for line in lines:
                results.append(f"  {line}")
        else:
            results.append("  (No messages captured)")
        
        # Clean up
        logging.getLogger().removeHandler(ch)
        log_capture_string.close()
    
    # Test default behavior (no LOG_LEVEL set)
    results.append(f"\n{'='*50}")
    results.append("Testing default behavior (no LOG_LEVEL)")
    results.append('='*50)
    
    if "LOG_LEVEL" in os.environ:
        del os.environ["LOG_LEVEL"]
    
    # Clear handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    setup_logging()
    
    results.append(f"Default root logger level: {logging.getLogger().level}")
    results.append(f"Expected level for default (0): {logging.CRITICAL}")
    
    # Write results to file
    with open("logging_test_results.txt", "w") as f:
        f.write("\n".join(results))
    
    print("Test completed! Results written to logging_test_results.txt")
    print("\nSummary of expected behavior:")
    print("- LOG_LEVEL=0: Should only show CRITICAL (level 50)")
    print("- LOG_LEVEL=1: Should show INFO and above (level 20)")  
    print("- LOG_LEVEL=2: Should show DEBUG and above (level 10)")
    print("- Default: Should be same as LOG_LEVEL=0")

if __name__ == "__main__":
    test_logging_levels()
