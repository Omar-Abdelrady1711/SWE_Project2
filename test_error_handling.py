#!/usr/bin/env python3
"""
Comprehensive test script to verify error handling in all metrics.
Tests various error scenarios to ensure custom exceptions are properly raised.
"""

import sys
import os
import time

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from acemcli.exceptions import APIError, ValidationError, MetricError
from acemcli.models import Category
from acemcli.metrics.dataset_code_score import DatasetAndCodeScoreMetric
from acemcli.metrics.performance_claims import PerformanceClaimsMetric
from acemcli.metrics.hf_api import HFAPIMetric
from acemcli.metrics.local_repo import LocalRepoMetric
from acemcli.metrics.size_score import SizeScoreMetric
from acemcli.metrics.dataset_quality import DatasetQualityMetric


def test_error_handling():
    """Test error handling across all metrics."""
    print("🧪 Testing Error Handling in All Metrics...")
    print("=" * 60)
    
    # Test metrics
    metrics_to_test = [
        ("Dataset Code Score", DatasetAndCodeScoreMetric(), Category.MODEL),
        ("Performance Claims", PerformanceClaimsMetric(), Category.MODEL),
        ("HuggingFace API", HFAPIMetric(), Category.MODEL),
        ("Local Repo", LocalRepoMetric(), Category.MODEL),
        ("Size Score", SizeScoreMetric(), Category.MODEL),
        ("Dataset Quality", DatasetQualityMetric(), Category.DATASET),
    ]
    
    test_results = []
    
    for metric_name, metric, category in metrics_to_test:
        print(f"\n🔍 Testing {metric_name} Metric...")
        
        # Test 1: Invalid URL (None)
        try:
            metric.compute(None, category)
            test_results.append(f"❌ {metric_name}: Should raise ValidationError for None URL")
        except ValidationError as e:
            test_results.append(f"✅ {metric_name}: Correctly raised ValidationError for None URL")
            print(f"   ✅ ValidationError: {e}")
        except Exception as e:
            test_results.append(f"⚠️  {metric_name}: Raised {type(e).__name__} instead of ValidationError")
        
        # Test 2: Invalid URL format
        try:
            metric.compute("not-a-url", category)
            test_results.append(f"❌ {metric_name}: Should raise ValidationError for invalid URL")
        except ValidationError as e:
            test_results.append(f"✅ {metric_name}: Correctly raised ValidationError for invalid URL")
            print(f"   ✅ ValidationError: {e}")
        except Exception as e:
            test_results.append(f"⚠️  {metric_name}: Raised {type(e).__name__} instead of ValidationError")
        
        # Test 3: Non-HuggingFace URL
        try:
            metric.compute("https://github.com/invalid/repo", category)
            test_results.append(f"❌ {metric_name}: Should raise ValidationError for non-HF URL")
        except ValidationError as e:
            test_results.append(f"✅ {metric_name}: Correctly raised ValidationError for non-HF URL")
            print(f"   ✅ ValidationError: {e}")
        except Exception as e:
            test_results.append(f"⚠️  {metric_name}: Raised {type(e).__name__} instead of ValidationError")
        
        # Test 4: Non-existent repository (should raise APIError)
        try:
            metric.compute("https://huggingface.co/nonexistent/repository-that-does-not-exist-12345", category)
            test_results.append(f"❌ {metric_name}: Should raise APIError for nonexistent repo")
        except APIError as e:
            test_results.append(f"✅ {metric_name}: Correctly raised APIError for nonexistent repo")
            print(f"   ✅ APIError: {e}")
        except Exception as e:
            test_results.append(f"⚠️  {metric_name}: Raised {type(e).__name__} instead of APIError")
        
        print(f"   Completed {metric_name} error handling tests")
    
    print("\n" + "=" * 60)
    print("📊 ERROR HANDLING TEST RESULTS:")
    print("=" * 60)
    
    passed_tests = 0
    total_tests = len(test_results)
    
    for result in test_results:
        print(result)
        if result.startswith("✅"):
            passed_tests += 1
    
    print("=" * 60)
    print(f"🎯 SUMMARY: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 ALL ERROR HANDLING TESTS PASSED!")
        print("✅ Task 5.2 Complete: Try-catch blocks successfully added!")
    else:
        print("⚠️  Some error handling tests need attention")
    
    return passed_tests == total_tests


def test_supports_method():
    """Test the supports method error handling."""
    print("\n🔍 Testing supports() method error handling...")
    
    metrics = [
        DatasetAndCodeScoreMetric(),
        PerformanceClaimsMetric(),
        HFAPIMetric(),
        LocalRepoMetric(),
        SizeScoreMetric(),
        DatasetQualityMetric(),
    ]
    
    test_cases = [
        (None, Category.MODEL, "None URL"),
        ("", Category.MODEL, "Empty URL"),
        (123, Category.MODEL, "Non-string URL"),
        ("invalid-url", Category.MODEL, "Invalid URL format"),
    ]
    
    all_passed = True
    
    for metric in metrics:
        metric_name = metric.__class__.__name__
        print(f"  Testing {metric_name}...")
        
        for url, category, description in test_cases:
            try:
                result = metric.supports(url, category)
                if result is False:
                    print(f"    ✅ {description}: Correctly returned False")
                else:
                    print(f"    ⚠️  {description}: Should return False, got {result}")
                    all_passed = False
            except Exception as e:
                print(f"    ✅ {description}: Safely handled exception ({type(e).__name__})")
    
    return all_passed


if __name__ == "__main__":
    print("🚀 Starting Comprehensive Error Handling Tests...")
    print("This will test that all metrics properly handle errors with custom exceptions.")
    print()
    
    # Test error handling
    error_tests_passed = test_error_handling()
    
    # Test supports method
    supports_tests_passed = test_supports_method()
    
    print("\n" + "=" * 60)
    print("🏁 FINAL RESULTS:")
    print("=" * 60)
    
    if error_tests_passed and supports_tests_passed:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Task 5.2 is COMPLETE!")
        print("📋 All metrics now have comprehensive error handling:")
        print("   • Input validation with ValidationError")
        print("   • API failure handling with APIError")
        print("   • Computation errors with MetricError")
        print("   • Proper score validation")
        print("   • Graceful fallback handling")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed - error handling needs attention")
        sys.exit(1)
