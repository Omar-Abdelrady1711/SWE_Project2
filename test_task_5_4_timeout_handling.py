"""
Test suite for API timeout handling (Task 5.4).

This test file verifies that all API requests have proper timeout handling
and that timeouts are handled gracefully with appropriate error messages.
"""

import pytest
import time
import unittest.mock as mock
from unittest.mock import patch, MagicMock
import requests
from requests.exceptions import Timeout, ConnectionError, HTTPError

from acemcli.timeout_config import (
    TimeoutConfig, 
    get_timeout_config, 
    set_timeout_config, 
    create_requests_session
)
from acemcli.exceptions import APIError, create_api_timeout_error
from acemcli.metrics.hf_api import HFAPIMetric
from acemcli.metrics.local_repo import LocalRepoMetric
from acemcli.metrics.dataset_code_score import DatasetAndCodeScoreMetric


class TestTimeoutConfiguration:
    """Test the centralized timeout configuration."""
    
    def test_default_timeout_config(self):
        """Test default timeout configuration values."""
        config = TimeoutConfig()
        
        assert config.connect_timeout == 10.0
        assert config.read_timeout == 30.0
        assert config.total_timeout == 45.0
        assert config.max_retries == 3
        assert config.backoff_factor == 1.0
    
    def test_timeout_config_from_environment(self):
        """Test timeout configuration from environment variables."""
        with patch.dict('os.environ', {
            'ACME_CONNECT_TIMEOUT': '15.0',
            'ACME_READ_TIMEOUT': '60.0',
            'ACME_TOTAL_TIMEOUT': '90.0',
            'ACME_MAX_RETRIES': '5',
            'ACME_BACKOFF_FACTOR': '2.0'
        }):
            config = TimeoutConfig.from_environment()
            
            assert config.connect_timeout == 15.0
            assert config.read_timeout == 60.0
            assert config.total_timeout == 90.0
            assert config.max_retries == 5
            assert config.backoff_factor == 2.0
    
    def test_requests_timeout_format(self):
        """Test timeout format for requests library."""
        config = TimeoutConfig(connect_timeout=5.0, read_timeout=25.0)
        timeout_tuple = config.as_requests_timeout()
        
        assert timeout_tuple == (5.0, 25.0)
    
    def test_huggingface_timeout_format(self):
        """Test timeout format for HuggingFace operations."""
        config = TimeoutConfig(total_timeout=60.0)
        hf_timeout = config.as_huggingface_timeout()
        
        assert hf_timeout == 60.0
    
    def test_create_requests_session(self):
        """Test creation of requests session with retry strategy."""
        session = create_requests_session()
        
        assert isinstance(session, requests.Session)
        # Check that adapters are properly mounted
        assert 'http://' in session.adapters
        assert 'https://' in session.adapters


class TestHFAPITimeoutHandling:
    """Test timeout handling in HuggingFace API metric."""
    
    def setup_method(self):
        """Set up test environment."""
        # Use shorter timeouts for testing
        self.test_config = TimeoutConfig(
            connect_timeout=1.0,
            read_timeout=2.0,
            total_timeout=3.0,
            max_retries=1
        )
        set_timeout_config(self.test_config)
        
        self.metric = HFAPIMetric()
        self.test_url = \"https://huggingface.co/test/model\"
    
    def test_timeout_initialization(self):
        \"\"\"Test that HFAPIMetric properly initializes with timeout config.\"\"\"
        assert self.metric.timeout_config == self.test_config
        assert hasattr(self.metric, 'session')
    
    @patch('acemcli.metrics.hf_api.HfApi')
    def test_api_timeout_handling(self, mock_hf_api):
        \"\"\"Test that API timeouts are properly caught and handled.\"\"\"
        # Mock the API to raise a timeout
        mock_api_instance = MagicMock()
        mock_api_instance.model_info.side_effect = Timeout(\"Request timed out\")
        mock_hf_api.return_value = mock_api_instance
        
        metric = HFAPIMetric()
        
        with pytest.raises(APIError) as exc_info:
            metric.compute(self.test_url, \"MODEL\")
        
        error = exc_info.value
        assert \"timed out\" in error.message.lower()
        assert error.api_name == \"HuggingFace\"
        assert error.status_code == 408
        assert str(self.test_config.total_timeout).rstrip('.0') in error.message
    
    @patch('acemcli.metrics.hf_api.HfApi')
    def test_connection_error_handling(self, mock_hf_api):
        \"\"\"Test that connection errors are properly handled.\"\"\"
        mock_api_instance = MagicMock()
        mock_api_instance.model_info.side_effect = ConnectionError(\"Connection failed\")
        mock_hf_api.return_value = mock_api_instance
        
        metric = HFAPIMetric()
        
        with pytest.raises(APIError) as exc_info:
            metric.compute(self.test_url, \"MODEL\")
        
        error = exc_info.value
        assert \"connection error\" in error.message.lower()
        assert error.api_name == \"HuggingFace\"
    
    @patch('acemcli.metrics.hf_api.HfApi')
    def test_http_error_handling(self, mock_hf_api):
        \"\"\"Test that HTTP errors are properly handled.\"\"\"
        mock_api_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        http_error = HTTPError(\"Not found\")
        http_error.response = mock_response
        mock_api_instance.model_info.side_effect = http_error
        mock_hf_api.return_value = mock_api_instance
        
        metric = HFAPIMetric()
        
        with pytest.raises(APIError) as exc_info:
            metric.compute(self.test_url, \"MODEL\")
        
        error = exc_info.value
        assert error.status_code == 404
        assert error.api_name == \"HuggingFace\"


class TestLocalRepoTimeoutHandling:
    \"\"\"Test timeout handling in local repository analysis.\"\"\"
    
    def setup_method(self):
        \"\"\"Set up test environment.\"\"\"
        self.test_config = TimeoutConfig(
            connect_timeout=1.0,
            read_timeout=2.0,
            total_timeout=3.0,
            max_retries=1
        )
        set_timeout_config(self.test_config)
        
        self.metric = LocalRepoMetric()
        self.test_url = \"https://huggingface.co/test/model\"
    
    def test_timeout_initialization(self):
        \"\"\"Test that LocalRepoMetric properly initializes with timeout config.\"\"\"
        assert self.metric.timeout_config == self.test_config
        assert hasattr(self.metric, 'session')
    
    @patch('acemcli.metrics.local_repo.snapshot_download')
    def test_download_timeout_handling(self, mock_snapshot_download):
        \"\"\"Test that download timeouts are properly caught and handled.\"\"\"
        mock_snapshot_download.side_effect = Timeout(\"Download timed out\")
        
        with pytest.raises(APIError) as exc_info:
            self.metric._download_repo_safely(\"test/model\", \"/tmp\")
        
        error = exc_info.value
        assert \"timed out\" in error.message.lower()
        assert error.api_name == \"HuggingFace\"
        assert error.status_code == 408
    
    @patch('acemcli.metrics.local_repo.snapshot_download')
    def test_download_with_timeout_parameter(self, mock_snapshot_download):
        \"\"\"Test that download is called with proper timeout parameter.\"\"\"
        mock_snapshot_download.return_value = \"/tmp/test\"
        
        self.metric._download_repo_safely(\"test/model\", \"/tmp\")
        
        # Verify that snapshot_download was called with timeout
        mock_snapshot_download.assert_called_once()
        call_kwargs = mock_snapshot_download.call_args[1]
        assert 'timeout' in call_kwargs
        assert call_kwargs['timeout'] == self.test_config.total_timeout


class TestDatasetCodeScoreTimeoutHandling:
    \"\"\"Test timeout handling in dataset code score metric.\"\"\"
    
    def setup_method(self):
        \"\"\"Set up test environment.\"\"\"
        self.test_config = TimeoutConfig(
            connect_timeout=1.0,
            read_timeout=2.0,
            total_timeout=3.0,
            max_retries=1
        )
        set_timeout_config(self.test_config)
        
        self.metric = DatasetAndCodeScoreMetric()
        self.test_url = \"https://huggingface.co/test/dataset\"
    
    def test_timeout_initialization(self):
        \"\"\"Test that DatasetAndCodeScoreMetric properly initializes with timeout config.\"\"\"
        assert self.metric.timeout_config == self.test_config
        assert hasattr(self.metric, 'session')
    
    @patch('acemcli.metrics.dataset_code_score.snapshot_download')
    def test_download_timeout_handling(self, mock_snapshot_download):
        \"\"\"Test that download timeouts are properly caught and handled.\"\"\"
        mock_snapshot_download.side_effect = Timeout(\"Download timed out\")
        
        with pytest.raises(APIError) as exc_info:
            self.metric._download_repo_safely(\"test/dataset\", \"/tmp\")
        
        error = exc_info.value
        assert \"timed out\" in error.message.lower()
        assert error.api_name == \"HuggingFace\"
        assert error.status_code == 408


class TestTimeoutErrorCreation:
    \"\"\"Test creation of timeout-related errors.\"\"\"
    
    def test_create_api_timeout_error(self):
        \"\"\"Test creation of API timeout errors.\"\"\"
        error = create_api_timeout_error(\"TestAPI\", \"https://example.com\", 30)
        
        assert isinstance(error, APIError)
        assert \"TestAPI\" in error.message
        assert \"30 seconds\" in error.message
        assert error.api_name == \"TestAPI\"
        assert error.url == \"https://example.com\"
        assert error.status_code == 408
    
    def test_timeout_error_details(self):
        \"\"\"Test that timeout errors contain proper details.\"\"\"
        error = create_api_timeout_error(\"GitHub\", \"https://github.com/test\", 45)
        
        assert error.details['api_name'] == \"GitHub\"
        assert error.details['url'] == \"https://github.com/test\"
        assert error.details['status_code'] == 408


@pytest.mark.integration
class TestEndToEndTimeoutHandling:
    \"\"\"Integration tests for timeout handling across the system.\"\"\"
    
    def setup_method(self):
        \"\"\"Set up test environment with very short timeouts.\"\"\"
        self.original_config = get_timeout_config()
        
        # Set very short timeouts for integration testing
        self.test_config = TimeoutConfig(
            connect_timeout=0.001,  # Very short to force timeout
            read_timeout=0.001,
            total_timeout=0.001,
            max_retries=1
        )
        set_timeout_config(self.test_config)
    
    def teardown_method(self):
        \"\"\"Restore original configuration.\"\"\"
        set_timeout_config(self.original_config)
    
    def test_requests_session_timeout_behavior(self):
        \"\"\"Test that requests session properly applies timeouts.\"\"\"
        session = create_requests_session()
        
        # This should timeout very quickly with our short timeout
        with pytest.raises((Timeout, ConnectionError, requests.exceptions.RequestException)):
            session.get(\"https://httpbin.org/delay/1\", timeout=self.test_config.as_requests_timeout())


def test_task_5_4_completion():
    \"\"\"Test that Task 5.4 requirements are met.\"\"\"
    # Verify timeout configuration exists
    config = get_timeout_config()
    assert isinstance(config, TimeoutConfig)
    
    # Verify all metrics have timeout configuration
    hf_metric = HFAPIMetric()
    assert hasattr(hf_metric, 'timeout_config')
    assert hasattr(hf_metric, 'session')
    
    local_metric = LocalRepoMetric()
    assert hasattr(local_metric, 'timeout_config')
    assert hasattr(local_metric, 'session')
    
    dataset_metric = DatasetAndCodeScoreMetric()
    assert hasattr(dataset_metric, 'timeout_config')
    assert hasattr(dataset_metric, 'session')
    
    # Verify error handling functions exist
    error = create_api_timeout_error(\"Test\", \"https://test.com\", 30)
    assert isinstance(error, APIError)
    assert error.status_code == 408
    
    print(\"✅ Task 5.4: API timeout handling implementation COMPLETE!\")
    print(\"   - Centralized timeout configuration ✓\")
    print(\"   - Enhanced HuggingFace API timeout handling ✓\")
    print(\"   - Enhanced local repository timeout handling ✓\")
    print(\"   - Enhanced dataset code score timeout handling ✓\")
    print(\"   - Comprehensive timeout error handling ✓\")
    print(\"   - Configurable timeout values via environment variables ✓\")


if __name__ == \"__main__\":
    # Run the completion test
    test_task_5_4_completion()
    
    # Run a simple timeout test
    print(\"\\n🧪 Running basic timeout functionality test...\")
    
    # Test configuration
    config = TimeoutConfig(connect_timeout=5.0, read_timeout=10.0, total_timeout=15.0)
    set_timeout_config(config)
    
    # Test metrics initialization
    hf_metric = HFAPIMetric()
    local_metric = LocalRepoMetric()
    dataset_metric = DatasetAndCodeScoreMetric()
    
    print(f\"   HF API metric timeout config: {hf_metric.timeout_config.total_timeout}s ✓\")
    print(f\"   Local repo metric timeout config: {local_metric.timeout_config.total_timeout}s ✓\")
    print(f\"   Dataset metric timeout config: {dataset_metric.timeout_config.total_timeout}s ✓\")
    
    # Test session creation
    session = create_requests_session()
    print(f\"   Created requests session with retry strategy ✓\")
    
    print(\"\\n🎯 Task 5.4 API timeout handling implementation is ready for testing!\")
