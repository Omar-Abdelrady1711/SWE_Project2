#!/usr/bin/env python3

import os
import sys
import logging
from pathlib import Path

# Add src to path  
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from acemcli.logging_setup import setup_logging
    
    results = []
    results.append("LOGGING VERIFICATION RESULTS")
    results.append("=" * 40)
    
    # Test LOG_LEVEL=0
    os.environ["LOG_LEVEL"] = "0"
    if "LOG_FILE" in os.environ:
        del os.environ["LOG_FILE"]
    
    # Clear handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    setup_logging()
    level_0 = logging.getLogger().level
    results.append(f"LOG_LEVEL=0: Root level = {level_0} (Expected: 50)")
    
    # Test LOG_LEVEL=1
    os.environ["LOG_LEVEL"] = "1"
    
    # Clear handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        
    setup_logging()
    level_1 = logging.getLogger().level
    results.append(f"LOG_LEVEL=1: Root level = {level_1} (Expected: 20)")
    
    # Test LOG_LEVEL=2
    os.environ["LOG_LEVEL"] = "2"
    
    # Clear handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        
    setup_logging()
    level_2 = logging.getLogger().level
    results.append(f"LOG_LEVEL=2: Root level = {level_2} (Expected: 10)")
    
    # Test default
    if "LOG_LEVEL" in os.environ:
        del os.environ["LOG_LEVEL"]
    
    # Clear handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        
    setup_logging()
    default_level = logging.getLogger().level
    results.append(f"Default (no LOG_LEVEL): Root level = {default_level} (Expected: 50)")
    
    # Summary
    results.append("")
    results.append("SUMMARY:")
    all_correct = (level_0 == 50 and level_1 == 20 and level_2 == 10 and default_level == 50)
    results.append(f"Overall: {'PASS' if all_correct else 'FAIL'}")
    
    if all_correct:
        results.append("✅ All logging levels are configured correctly!")
    else:
        results.append("❌ Some logging levels are not configured correctly")
        
    # Write to file
    with open("verification_results.txt", "w") as f:
        f.write("\n".join(results))
        
    print("Verification completed! Check verification_results.txt")
    
except Exception as e:
    with open("verification_error.txt", "w") as f:
        f.write(f"Error during verification: {e}")
        import traceback
        f.write(f"\nTraceback:\n{traceback.format_exc()}")
    print(f"Error: {e}")
