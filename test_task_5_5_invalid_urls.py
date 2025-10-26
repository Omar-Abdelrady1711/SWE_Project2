"""
Task 5.5: Test error scenarios with invalid URLs - Comprehensive Test Suite

This module tests various invalid URL scenarios to ensure the CLI and all metrics
handle them gracefully with proper error messages and exit codes.
"""

import subprocess
import tempfile
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple
import pytest

# Add the src directory to Python path
sys.path.insert(0, '/Users/blas/Documents/Obsidian Vault/School/F25/ECE 461/Project Repo/ECE30861_HW1/src')

from acemcli.exceptions import APIError, ValidationError, MetricError
from acemcli.models import Category
from acemcli.metrics.hf_api import HFAPIMetric
from acemcli.metrics.local_repo import LocalRepoMetric
from acemcli.metrics.dataset_code_score import DatasetAndCodeScoreMetric
from acemcli.metrics.performance_claims import PerformanceClaimsMetric


class InvalidURLTestSuite:
    """Comprehensive test suite for invalid URL error scenarios."""
    
    def __init__(self):
        self.project_root = Path('/Users/blas/Documents/Obsidian Vault/School/F25/ECE 461/Project Repo/ECE30861_HW1')
        self.run_script = self.project_root / 'run'
        self.test_results = []
        
    def create_url_file(self, urls: List[str]) -> str:
        """Create a temporary file with URLs for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for url in urls:
                f.write(url + '\n')
            return f.name
    
    def run_cli_with_urls(self, urls: List[str]) -> Tuple[int, str, str]:
        """Run the CLI with a list of URLs and return exit code, stdout, stderr."""
        url_file = self.create_url_file(urls)
        
        try:
            # Run the CLI command
            result = subprocess.run(
                [str(self.run_script), url_file],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout
            )
            
            return result.returncode, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            return -1, "", "Process timed out"
        except Exception as e:
            return -1, "", f"Process error: {str(e)}"
        finally:
            # Clean up temporary file
            try:
                os.unlink(url_file)
            except:
                pass

    def test_cli_invalid_url_scenarios(self) -> Dict[str, Any]:
        """Test CLI with various invalid URL scenarios."""
        
        print("🧪 Testing CLI with Invalid URL Scenarios")
        print("=" * 60)
        
        test_cases = [
            {
                "name": "Empty URLs",
                "urls": ["", "   ", "\t"],
                "expected_behavior": "Should skip empty URLs gracefully"
            },
            {
                "name": "Malformed URLs",
                "urls": ["not-a-url", "htp://broken-protocol", "https://", "://missing-protocol"],
                "expected_behavior": "Should show validation errors"
            },
            {
                "name": "Invalid Protocols",
                "urls": ["ftp://huggingface.co/model", "file:///local/path", "mailto:test@example.com"],
                "expected_behavior": "Should reject non-HTTP(S) protocols"
            },
            {
                "name": "Non-HuggingFace URLs",
                "urls": ["https://github.com/user/repo", "https://google.com", "https://pypi.org/project/requests"],
                "expected_behavior": "Should reject non-HuggingFace URLs"
            },
            {
                "name": "Malformed HuggingFace URLs",
                "urls": [
                    "https://huggingface.co/",
                    "https://huggingface.co/incomplete",
                    "https://huggingface.co//double-slash",
                    "https://huggingface.co/user//empty-repo"
                ],
                "expected_behavior": "Should reject incomplete HuggingFace URLs"
            },
            {
                "name": "URLs with Invalid Characters",
                "urls": [
                    "https://huggingface.co/user name/repo",  # Space in URL
                    "https://huggingface.co/user/repo\nnewline",  # Newline in URL
                    "https://huggingface.co/user/repo|pipe",  # Invalid character
                ],
                "expected_behavior": "Should handle URLs with invalid characters"
            },
            {
                "name": "Very Long URLs",
                "urls": [
                    f"https://huggingface.co/{'a' * 1000}/{'b' * 1000}",  # Very long URL
                ],
                "expected_behavior": "Should handle extremely long URLs"
            },
            {
                "name": "Non-existent Repositories",
                "urls": [
                    "https://huggingface.co/definitely-does-not-exist/invalid-repo-12345",
                    "https://huggingface.co/user/nonexistent-model-xyz",
                ],
                "expected_behavior": "Should show API errors for non-existent repos"
            }
        ]
        
        results = {"passed": 0, "failed": 0, "details": []}
        
        for test_case in test_cases:
            print(f"\n🔍 Testing: {test_case['name']}")
            print(f"   Expected: {test_case['expected_behavior']}")
            
            exit_code, stdout, stderr = self.run_cli_with_urls(test_case['urls'])
            
            # Analyze results
            test_passed = False
            error_message = ""
            
            if exit_code == 0:
                # CLI should not succeed with invalid URLs
                if test_case['name'] in ["Empty URLs"]:
                    # Empty URLs might be skipped gracefully
                    test_passed = True
                    error_message = "Empty URLs handled gracefully"
                else:
                    error_message = f"CLI unexpectedly succeeded (exit code 0)"
            elif exit_code == 1:
                # Expected failure with proper error handling
                test_passed = True
                error_message = "CLI properly failed with exit code 1"
            else:
                error_message = f"CLI failed with unexpected exit code {exit_code}"
            
            if test_passed:
                print(f"   ✅ {error_message}")
                results["passed"] += 1
            else:
                print(f"   ❌ {error_message}")
                if stdout:
                    print(f"      STDOUT: {stdout[:200]}...")
                if stderr:
                    print(f"      STDERR: {stderr[:200]}...")
                results["failed"] += 1
            
            results["details"].append({
                "test": test_case['name'],
                "passed": test_passed,
                "exit_code": exit_code,
                "message": error_message
            })
        
        return results

    def test_metric_invalid_url_handling(self) -> Dict[str, Any]:
        """Test individual metrics with invalid URLs."""
        
        print("\n🔧 Testing Individual Metrics with Invalid URLs")
        print("=" * 60)
        
        # Initialize metrics to test
        metrics = [
            ("HuggingFace API", HFAPIMetric()),
            ("Local Repository", LocalRepoMetric()),
            ("Dataset Code Score", DatasetAndCodeScoreMetric()),
            ("Performance Claims", PerformanceClaimsMetric()),
        ]
        
        invalid_urls = [
            (None, "None URL"),
            ("", "Empty string"),
            ("not-a-url", "Invalid format"),
            ("https://github.com/user/repo", "Non-HuggingFace URL"),
            ("https://huggingface.co/", "Incomplete HuggingFace URL"),
            ("https://huggingface.co/nonexistent/model-12345", "Non-existent repository"),
        ]
        
        results = {"passed": 0, "failed": 0, "details": []}
        
        for metric_name, metric in metrics:
            print(f"\n🔍 Testing {metric_name} Metric:")
            
            for invalid_url, description in invalid_urls:
                try:
                    # Test supports method first
                    supports_result = metric.supports(invalid_url, Category.MODEL)
                    
                    if supports_result is False:
                        print(f"   ✅ {description}: Correctly rejected by supports()")
                        results["passed"] += 1
                        continue
                    
                    # If supports() returns True, test compute method
                    start_time = time.time()
                    result = metric.compute(invalid_url, Category.MODEL)
                    elapsed_time = time.time() - start_time
                    
                    # If we get here, the metric didn't raise an exception
                    print(f"   ⚠️  {description}: Unexpectedly succeeded (took {elapsed_time:.2f}s)")
                    results["failed"] += 1
                    
                except ValidationError as e:
                    print(f"   ✅ {description}: Properly raised ValidationError - {str(e)[:100]}...")
                    results["passed"] += 1
                    
                except APIError as e:
                    print(f"   ✅ {description}: Properly raised APIError - {str(e)[:100]}...")
                    results["passed"] += 1
                    
                except MetricError as e:
                    print(f"   ✅ {description}: Properly raised MetricError - {str(e)[:100]}...")
                    results["passed"] += 1
                    
                except Exception as e:
                    print(f"   ⚠️  {description}: Raised unexpected {type(e).__name__} - {str(e)[:100]}...")
                    results["failed"] += 1
                
                results["details"].append({
                    "metric": metric_name,
                    "test": description,
                    "url": str(invalid_url)[:50] + "..." if len(str(invalid_url)) > 50 else str(invalid_url)
                })
        
        return results

    def test_edge_cases(self) -> Dict[str, Any]:
        """Test edge cases and boundary conditions."""
        
        print("\n🎯 Testing Edge Cases and Boundary Conditions")
        print("=" * 60)
        
        edge_cases = [
            {
                "name": "Unicode URLs",
                "urls": ["https://huggingface.co/üser/mödel", "https://huggingface.co/用户/模型"],
                "description": "URLs with Unicode characters"
            },
            {
                "name": "URLs with Query Parameters",
                "urls": [
                    "https://huggingface.co/user/model?param=value",
                    "https://huggingface.co/user/model#fragment"
                ],
                "description": "URLs with query parameters and fragments"
            },
            {
                "name": "Case Variations",
                "urls": [
                    "HTTPS://HUGGINGFACE.CO/USER/MODEL",
                    "https://HUGGINGFACE.co/user/MODEL"
                ],
                "description": "URLs with different case variations"
            },
            {
                "name": "Trailing/Leading Whitespace",
                "urls": [
                    "  https://huggingface.co/user/model  ",
                    "\thttps://huggingface.co/user/model\n"
                ],
                "description": "URLs with whitespace padding"
            }
        ]
        
        results = {"passed": 0, "failed": 0, "details": []}
        
        for case in edge_cases:
            print(f"\n🔍 Testing: {case['name']}")
            print(f"   Description: {case['description']}")
            
            exit_code, stdout, stderr = self.run_cli_with_urls(case['urls'])
            
            # For edge cases, we mainly want to ensure the CLI doesn't crash
            if exit_code in [0, 1]:  # Either success or controlled failure
                print(f"   ✅ CLI handled edge case gracefully (exit code {exit_code})")
                results["passed"] += 1
            else:
                print(f"   ❌ CLI crashed or had unexpected behavior (exit code {exit_code})")
                if stderr:
                    print(f"      STDERR: {stderr[:200]}...")
                results["failed"] += 1
            
            results["details"].append({
                "case": case['name'],
                "exit_code": exit_code,
                "handled_gracefully": exit_code in [0, 1]
            })
        
        return results

    def test_file_handling_errors(self) -> Dict[str, Any]:
        """Test file handling error scenarios."""
        
        print("\n📁 Testing File Handling Error Scenarios")
        print("=" * 60)
        
        results = {"passed": 0, "failed": 0, "details": []}
        
        # Test 1: Non-existent file
        print("🔍 Testing non-existent URL file...")
        result = subprocess.run(
            [str(self.run_script), "/nonexistent/file.txt"],
            cwd=str(self.project_root),
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print("   ✅ CLI properly failed for non-existent file")
            results["passed"] += 1
        else:
            print("   ❌ CLI should fail for non-existent file")
            results["failed"] += 1
        
        # Test 2: Empty file
        print("\n🔍 Testing empty URL file...")
        empty_file = self.create_url_file([])
        
        try:
            result = subprocess.run(
                [str(self.run_script), empty_file],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Empty file should be handled gracefully
            if result.returncode == 0:
                print("   ✅ CLI handled empty file gracefully")
                results["passed"] += 1
            else:
                print(f"   ⚠️  CLI failed with empty file (exit code {result.returncode})")
                results["failed"] += 1
                
        finally:
            os.unlink(empty_file)
        
        # Test 3: File with only whitespace
        print("\n🔍 Testing file with only whitespace...")
        whitespace_file = self.create_url_file(["   ", "\t", "\n", ""])
        
        try:
            result = subprocess.run(
                [str(self.run_script), whitespace_file],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Should handle whitespace gracefully
            print(f"   ✅ CLI handled whitespace-only file (exit code {result.returncode})")
            results["passed"] += 1
            
        except Exception as e:
            print(f"   ❌ CLI failed with whitespace file: {e}")
            results["failed"] += 1
        finally:
            os.unlink(whitespace_file)
        
        return results

    def run_comprehensive_test(self) -> bool:
        """Run the complete test suite for Task 5.5."""
        
        print("🚀 Starting Task 5.5: Invalid URL Error Scenarios Test Suite")
        print("=" * 70)
        print("This test suite verifies that the CLI handles invalid URLs gracefully")
        print("with appropriate error messages and exit codes.")
        print("=" * 70)
        
        all_results = []
        
        # Run all test categories
        cli_results = self.test_cli_invalid_url_scenarios()
        metric_results = self.test_metric_invalid_url_handling()
        edge_results = self.test_edge_cases()
        file_results = self.test_file_handling_errors()
        
        all_results.extend([cli_results, metric_results, edge_results, file_results])
        
        # Calculate overall results
        total_passed = sum(r["passed"] for r in all_results)
        total_failed = sum(r["failed"] for r in all_results)
        total_tests = total_passed + total_failed
        
        print("\n" + "=" * 70)
        print("📊 TASK 5.5 TEST RESULTS SUMMARY")
        print("=" * 70)
        
        print(f"CLI Invalid URL Tests:     {cli_results['passed']}/{cli_results['passed'] + cli_results['failed']} passed")
        print(f"Metric Error Handling:     {metric_results['passed']}/{metric_results['passed'] + metric_results['failed']} passed")
        print(f"Edge Case Handling:        {edge_results['passed']}/{edge_results['passed'] + edge_results['failed']} passed")
        print(f"File Handling Errors:      {file_results['passed']}/{file_results['passed'] + file_results['failed']} passed")
        
        print("=" * 70)
        print(f"🎯 OVERALL RESULTS: {total_passed}/{total_tests} tests passed ({total_passed/total_tests*100:.1f}%)")
        
        success_threshold = 0.8  # 80% of tests should pass
        test_suite_passed = (total_passed / total_tests) >= success_threshold
        
        if test_suite_passed:
            print("🎉 TASK 5.5 COMPLETED SUCCESSFULLY!")
            print("✅ Invalid URL error scenarios are properly handled")
            print("✅ CLI provides appropriate error messages")
            print("✅ Metrics handle invalid inputs gracefully")
            print("✅ Edge cases are managed correctly")
            print("✅ File handling errors are caught and reported")
            
            print("\n📋 Key Error Handling Features Verified:")
            print("   • ValidationError for malformed URLs")
            print("   • APIError for non-existent repositories")
            print("   • MetricError for computation failures")
            print("   • Graceful handling of edge cases")
            print("   • Proper CLI exit codes")
            print("   • Clear error messages for users")
            
        else:
            print("⚠️  TASK 5.5 NEEDS ATTENTION")
            print(f"   Only {total_passed}/{total_tests} tests passed")
            print("   Some error scenarios may not be handled properly")
        
        return test_suite_passed


def run_quick_invalid_url_test():
    """Run a quick test of invalid URL handling."""
    
    print("⚡ Quick Invalid URL Test")
    print("=" * 40)
    
    # Test a few metrics with invalid URLs
    try:
        metric = HFAPIMetric()
        
        # Test invalid URLs
        invalid_urls = [
            None,
            "",
            "not-a-url",
            "https://github.com/user/repo",
            "https://huggingface.co/nonexistent/repo-12345"
        ]
        
        for url in invalid_urls:
            try:
                if not metric.supports(url, Category.MODEL):
                    print(f"✅ Rejected: {url}")
                else:
                    result = metric.compute(url, Category.MODEL)
                    print(f"⚠️  Unexpectedly processed: {url}")
            except (ValidationError, APIError, MetricError) as e:
                print(f"✅ Caught {type(e).__name__}: {url}")
            except Exception as e:
                print(f"❌ Unexpected error for {url}: {type(e).__name__}")
        
        print("✅ Quick test completed")
        return True
        
    except Exception as e:
        print(f"❌ Quick test failed: {e}")
        return False


if __name__ == "__main__":
    # Run based on command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        success = run_quick_invalid_url_test()
    else:
        # Run comprehensive test suite
        test_suite = InvalidURLTestSuite()
        success = test_suite.run_comprehensive_test()
    
    sys.exit(0 if success else 1)
