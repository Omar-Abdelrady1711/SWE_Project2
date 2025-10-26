#!/usr/bin/env python3
"""
Quick test script to verify custom exceptions are working correctly.
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from acemcli.exceptions import (
    APIError,
    ValidationError, 
    MetricError,
    create_api_timeout_error,
    create_invalid_url_error,
    create_metric_score_error
)

def test_exceptions():
    """Test all custom exception classes."""
    print("🧪 Testing Custom Exception Classes...")
    
    # Test APIError
    try:
        raise APIError(
            "HuggingFace API request failed",
            api_name="HuggingFace",
            status_code=404,
            url="https://huggingface.co/invalid-model"
        )
    except APIError as e:
        print(f"✅ APIError: {e}")
        print(f"   - API Name: {e.api_name}")
        print(f"   - Status Code: {e.status_code}")
        print(f"   - URL: {e.url}")
    
    # Test ValidationError
    try:
        raise ValidationError(
            "Invalid URL format",
            field_name="model_url",
            invalid_value="not-a-url",
            expected_format="Valid HTTP/HTTPS URL"
        )
    except ValidationError as e:
        print(f"✅ ValidationError: {e}")
        print(f"   - Field: {e.field_name}")
        print(f"   - Invalid Value: {e.invalid_value}")
    
    # Test MetricError
    try:
        raise MetricError(
            "Failed to compute bus factor",
            metric_name="bus_factor",
            url="https://github.com/example/repo",
            computation_step="contributor_analysis"
        )
    except MetricError as e:
        print(f"✅ MetricError: {e}")
        print(f"   - Metric: {e.metric_name}")
        print(f"   - Step: {e.computation_step}")
    
    # Test convenience functions
    timeout_error = create_api_timeout_error("GitHub", "https://api.github.com/repos/test/test", 30)
    print(f"✅ Timeout Error: {timeout_error}")
    
    url_error = create_invalid_url_error("invalid-url", "Missing protocol")
    print(f"✅ URL Error: {url_error}")
    
    score_error = create_metric_score_error("license", 1.5)
    print(f"✅ Score Error: {score_error}")
    
    print("\n🎉 All exception classes working correctly!")
    print("✅ Task 5.1 Complete: Custom exception classes created successfully!")

if __name__ == "__main__":
    test_exceptions()
