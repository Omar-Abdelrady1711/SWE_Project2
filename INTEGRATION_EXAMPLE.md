# 🚀 INTEGRATION EXAMPLE: How to Add Exception Handling

## Example: Integrating exceptions into `dataset_code_score.py`

Here's how to add the custom exceptions to your existing metric:

```python
# Add to imports at the top of dataset_code_score.py
from acemcli.exceptions import MetricError, APIError, ValidationError, create_missing_data_error

class DatasetAndCodeScoreMetric:

    def calculate(self, url: str, repo_info: Dict[str, Any]) -> MetricResult:
        """Calculate dataset and code score with proper error handling."""
        start_time = time.time()

        try:
            # Validate URL first
            if not url or not isinstance(url, str):
                raise ValidationError(
                    "Invalid URL provided for dataset code score",
                    field_name="url",
                    invalid_value=url,
                    expected_format="Non-empty string URL"
                )

            # Main computation with error handling
            try:
                score = self._compute_score(url, repo_info)

                # Validate score range
                if not 0 <= score <= 1:
                    raise ValidationError(
                        f"Dataset code score must be between 0 and 1, got {score}",
                        field_name="dataset_code_score",
                        invalid_value=score,
                        expected_format="Float between 0.0 and 1.0"
                    )

            except Exception as e:
                # Wrap any computation errors in MetricError
                raise MetricError(
                    "Failed to compute dataset and code score",
                    metric_name="dataset_and_code_score",
                    url=url,
                    computation_step="score_calculation",
                    original_exception=e
                )

            latency = int((time.time() - start_time) * 1000)

            return MetricResult(
                name="dataset_and_code_score",
                score=score,
                latency=latency,
                category=Category.MODEL
            )

        except (ValidationError, MetricError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Catch any other unexpected errors
            latency = int((time.time() - start_time) * 1000)
            raise MetricError(
                f"Unexpected error in dataset code score calculation: {str(e)}",
                metric_name="dataset_and_code_score",
                url=url,
                computation_step="unexpected_error",
                original_exception=e
            )

    def _download_repo_safely(self, repo_id: str) -> Path:
        """Download repository with API error handling."""
        try:
            return snapshot_download(repo_id=repo_id, local_dir=temp_dir)
        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                raise APIError(
                    f"Repository not found: {repo_id}",
                    api_name="HuggingFace",
                    status_code=404,
                    url=f"https://huggingface.co/{repo_id}"
                )
            elif "timeout" in str(e).lower():
                raise APIError(
                    f"Timeout downloading repository: {repo_id}",
                    api_name="HuggingFace",
                    status_code=408,
                    url=f"https://huggingface.co/{repo_id}"
                )
            else:
                raise APIError(
                    f"Failed to download repository: {str(e)}",
                    api_name="HuggingFace",
                    url=f"https://huggingface.co/{repo_id}",
                    original_exception=e
                )
```

## 🔧 Key Integration Patterns

### 1. **Input Validation**

```python
if not url or not isinstance(url, str):
    raise ValidationError("Invalid URL", field_name="url", invalid_value=url)
```

### 2. **API Call Protection**

```python
try:
    api_response = some_api_call()
except requests.Timeout:
    raise create_api_timeout_error("HuggingFace", url, 30)
except requests.HTTPError as e:
    raise APIError("API failed", api_name="HuggingFace", status_code=e.response.status_code)
```

### 3. **Metric Computation Protection**

```python
try:
    score = complex_calculation()
    if not 0 <= score <= 1:
        raise create_metric_score_error("metric_name", score)
except Exception as e:
    raise MetricError("Calculation failed", metric_name="...", original_exception=e)
```

### 4. **Score Validation**

```python
if not 0 <= score <= 1:
    raise create_metric_score_error("dataset_code_score", score)
```

This pattern should be applied to **all your metrics** in Tasks 5.2-5.5! 🎯
