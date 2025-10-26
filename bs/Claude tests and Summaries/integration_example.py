#!/usr/bin/env python3
"""
Example: How to integrate logging_setup in your CLI commands
"""

import logging
from acemcli.logging_setup import setup_logging

def main():
    # Set up logging first thing in your CLI
    setup_logging()
    
    # Get a logger for your module
    logger = logging.getLogger("acme_cli")
    
    # Now you can log throughout your application
    logger.debug("Starting application")
    logger.info("Processing URL file...")
    logger.warning("Rate limit approaching")
    logger.error("Failed to fetch model data")
    logger.critical("Application crashed")

# Example usage in different commands:

def install_command():
    setup_logging()
    logger = logging.getLogger("install")
    logger.info("Installing dependencies...")
    # Your install logic here
    
def score_command(url_file):
    setup_logging()
    logger = logging.getLogger("score")
    logger.info(f"Processing URL file: {url_file}")
    # Your scoring logic here
    
def test_command():
    setup_logging() 
    logger = logging.getLogger("test")
    logger.info("Running test suite...")
    # Your test logic here

if __name__ == "__main__":
    main()
