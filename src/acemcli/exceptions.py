"""
Custom exception classes for ACME CLI tool.

This module defines custom exception classes used throughout the application
for better error handling and debugging.
"""

from typing import Optional, Any


class ACMEBaseException(Exception):
    """Base exception class for all ACME CLI exceptions."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        """
        Initialize the base exception.
        
        Args:
            message: Human-readable error message
            details: Optional dictionary with additional error details
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} - Details: {self.details}"
        return self.message


class APIError(ACMEBaseException):
    """
    Exception raised when API calls fail.
    
    This includes errors from:
    - HuggingFace Hub API
    - GitHub API
    - Network connectivity issues
    - Rate limiting
    - Authentication failures
    """
    
    def __init__(
        self, 
        message: str, 
        api_name: Optional[str] = None,
        status_code: Optional[int] = None,
        response_data: Optional[Any] = None,
        url: Optional[str] = None
    ):
        """
        Initialize API error.
        
        Args:
            message: Human-readable error message
            api_name: Name of the API that failed (e.g., 'HuggingFace', 'GitHub')
            status_code: HTTP status code if applicable
            response_data: Raw response data from the API
            url: The URL that was being accessed when the error occurred
        """
        details = {}
        if api_name:
            details['api_name'] = api_name
        if status_code:
            details['status_code'] = status_code
        if response_data:
            details['response_data'] = response_data
        if url:
            details['url'] = url
            
        super().__init__(message, details)
        self.api_name = api_name
        self.status_code = status_code
        self.response_data = response_data
        self.url = url


class ValidationError(ACMEBaseException):
    """
    Exception raised when input validation fails.
    
    This includes errors from:
    - Invalid URLs
    - Malformed input files
    - Invalid configuration values
    - Missing required parameters
    - Invalid metric scores (outside [0,1] range)
    """
    
    def __init__(
        self, 
        message: str, 
        field_name: Optional[str] = None,
        invalid_value: Optional[Any] = None,
        expected_format: Optional[str] = None
    ):
        """
        Initialize validation error.
        
        Args:
            message: Human-readable error message
            field_name: Name of the field that failed validation
            invalid_value: The value that failed validation
            expected_format: Description of the expected format
        """
        details = {}
        if field_name:
            details['field_name'] = field_name
        if invalid_value is not None:
            details['invalid_value'] = invalid_value
        if expected_format:
            details['expected_format'] = expected_format
            
        super().__init__(message, details)
        self.field_name = field_name
        self.invalid_value = invalid_value
        self.expected_format = expected_format


class MetricError(ACMEBaseException):
    """
    Exception raised when metric computation fails.
    
    This includes errors from:
    - Metric calculation failures
    - Missing required data for metric computation
    - Timeout errors during metric calculation
    - Invalid metric results
    - Local repository analysis failures
    """
    
    def __init__(
        self, 
        message: str, 
        metric_name: Optional[str] = None,
        url: Optional[str] = None,
        computation_step: Optional[str] = None,
        original_exception: Optional[Exception] = None
    ):
        """
        Initialize metric computation error.
        
        Args:
            message: Human-readable error message
            metric_name: Name of the metric that failed (e.g., 'bus_factor', 'license')
            url: The URL being analyzed when the error occurred
            computation_step: The step in metric computation that failed
            original_exception: The original exception that caused this error
        """
        details = {}
        if metric_name:
            details['metric_name'] = metric_name
        if url:
            details['url'] = url
        if computation_step:
            details['computation_step'] = computation_step
        if original_exception:
            details['original_exception'] = str(original_exception)
            details['exception_type'] = type(original_exception).__name__
            
        super().__init__(message, details)
        self.metric_name = metric_name
        self.url = url
        self.computation_step = computation_step
        self.original_exception = original_exception


# Convenience functions for common error scenarios

def create_api_timeout_error(api_name: str, url: str, timeout_seconds: int) -> APIError:
    """Create a standardized API timeout error."""
    return APIError(
        f"{api_name} API request timed out after {timeout_seconds} seconds",
        api_name=api_name,
        url=url,
        status_code=408
    )


def create_api_rate_limit_error(api_name: str, reset_time: Optional[str] = None) -> APIError:
    """Create a standardized API rate limit error."""
    message = f"{api_name} API rate limit exceeded"
    if reset_time:
        message += f". Retry after {reset_time}"
    
    return APIError(
        message,
        api_name=api_name,
        status_code=429,
        response_data={'reset_time': reset_time} if reset_time else None
    )


def create_invalid_url_error(url: str, reason: str = "Invalid format") -> ValidationError:
    """Create a standardized invalid URL error."""
    return ValidationError(
        f"Invalid URL: {reason}",
        field_name="url",
        invalid_value=url,
        expected_format="Valid HTTP/HTTPS URL"
    )


def create_metric_score_error(metric_name: str, score: float) -> ValidationError:
    """Create a standardized metric score validation error."""
    return ValidationError(
        f"Metric score must be between 0 and 1, got {score}",
        field_name=f"{metric_name}_score",
        invalid_value=score,
        expected_format="Float between 0.0 and 1.0"
    )


def create_missing_data_error(metric_name: str, missing_field: str, url: str) -> MetricError:
    """Create a standardized missing data error for metric computation."""
    return MetricError(
        f"Cannot compute {metric_name}: missing required field '{missing_field}'",
        metric_name=metric_name,
        url=url,
        computation_step="data_validation"
    )
