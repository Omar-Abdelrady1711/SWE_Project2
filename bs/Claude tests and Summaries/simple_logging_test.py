#!/usr/bin/env python3
"""
Simple manual test for logging_setup.py
"""

import os
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from acemcli.logging_setup import setup_logging

def manual_test():
    print("=== MANUAL LOGGING TEST ===")
    
    print("\n1. Testing LOG_LEVEL=0 (Critical only)")
    os.environ["LOG_LEVEL"] = "0"
    if "LOG_FILE" in os.environ:
        del os.environ["LOG_FILE"]
    
    # Clear handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    setup_logging()
    logger = logging.getLogger("test")
    
    print("Expected: Only CRITICAL should appear")
    logger.critical("CRITICAL message")
    logger.error("ERROR message") 
    logger.warning("WARNING message")
    logger.info("INFO message")
    logger.debug("DEBUG message")
    
    print("\n2. Testing LOG_LEVEL=1 (Info and above)")
    os.environ["LOG_LEVEL"] = "1"
    
    # Clear handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    setup_logging()
    logger = logging.getLogger("test2")
    
    print("Expected: CRITICAL, ERROR, WARNING, INFO should appear")
    logger.critical("CRITICAL message")
    logger.error("ERROR message")
    logger.warning("WARNING message") 
    logger.info("INFO message")
    logger.debug("DEBUG message")
    
    print("\n3. Testing LOG_LEVEL=2 (Debug and above)")
    os.environ["LOG_LEVEL"] = "2"
    
    # Clear handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    setup_logging()
    logger = logging.getLogger("test3")
    
    print("Expected: All messages should appear")
    logger.critical("CRITICAL message")
    logger.error("ERROR message") 
    logger.warning("WARNING message")
    logger.info("INFO message")
    logger.debug("DEBUG message")

if __name__ == "__main__":
    manual_test()
