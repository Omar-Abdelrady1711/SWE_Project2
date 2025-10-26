#!/usr/bin/env python3

import os
import sys
from pathlib import Path

print("Python version:", sys.version)
print("Current working directory:", os.getcwd())

# Add src to path
src_path = str(Path(__file__).parent / "src")
print(f"Adding to path: {src_path}")
sys.path.insert(0, src_path)

try:
    print("Attempting to import logging_setup...")
    from acemcli.logging_setup import setup_logging
    print("✅ Import successful!")
    
    print("Testing basic setup...")
    os.environ["LOG_LEVEL"] = "1"
    setup_logging()
    print("✅ setup_logging() executed without error!")
    
    import logging
    logger = logging.getLogger("test")
    print(f"Root logger level: {logging.getLogger().level}")
    
    logger.info("Test message")
    print("✅ Test completed successfully!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
