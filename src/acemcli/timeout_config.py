"""
Centralized timeout configuration for API requests.

This module provides consistent timeout handling across all API operations
in the ACME CLI tool.
"""

import os
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class TimeoutConfig:
    """Configuration for API request timeouts."""
    
    # Default timeout values (in seconds)
    connect_timeout: float = 10.0    # Time to establish connection
    read_timeout: float = 30.0       # Time to read response
    total_timeout: float = 45.0      # Total time for the entire request
    
    # Retry configuration
    max_retries: int = 3
    backoff_factor: float = 1.0      # Multiplier for retry delays
    
    @classmethod
    def from_environment(cls) -> 'TimeoutConfig':
        """Create timeout configuration from environment variables."""
        return cls(
            connect_timeout=float(os.getenv('ACME_CONNECT_TIMEOUT', 10.0)),
            read_timeout=float(os.getenv('ACME_READ_TIMEOUT', 30.0)),
            total_timeout=float(os.getenv('ACME_TOTAL_TIMEOUT', 45.0)),
            max_retries=int(os.getenv('ACME_MAX_RETRIES', 3)),
            backoff_factor=float(os.getenv('ACME_BACKOFF_FACTOR', 1.0))
        )
    
    def as_requests_timeout(self) -> Tuple[float, float]:
        """Return timeout values in format expected by requests library."""
        return (self.connect_timeout, self.read_timeout)
    
    def as_huggingface_timeout(self) -> float:
        """Return timeout value for HuggingFace operations."""
        return self.total_timeout


# Global timeout configuration instance
DEFAULT_TIMEOUT_CONFIG = TimeoutConfig.from_environment()


def get_timeout_config() -> TimeoutConfig:
    """Get the current timeout configuration."""
    return DEFAULT_TIMEOUT_CONFIG


def set_timeout_config(config: TimeoutConfig) -> None:
    """Set a new timeout configuration."""
    global DEFAULT_TIMEOUT_CONFIG
    DEFAULT_TIMEOUT_CONFIG = config


def create_requests_session():
    """Create a requests session with proper timeout configuration."""
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    
    config = get_timeout_config()
    
    # Create retry strategy
    retry_strategy = Retry(
        total=config.max_retries,
        backoff_factor=config.backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],  # Retry on these HTTP status codes
        method_whitelist=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
    )
    
    # Create session with retry adapter
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session
