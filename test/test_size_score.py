from acemcli.metrics.size_score import SizeScoreMetric

def test_supports_size_metric_model_url():
    m = SizeScoreMetric()
    assert m.supports("https://huggingface.co/google/gemma-3-270m", "MODEL")

def test_does_not_support_dataset_or_code():
    m = SizeScoreMetric()
    assert not m.supports("https://huggingface.co/datasets/squad", "DATASET")
    assert not m.supports("https://github.com/user/repo", "CODE")

def test_compute_returns_metricresult_fields(tmp_path):
    m = SizeScoreMetric()
    result = m.compute("https://huggingface.co/google/gemma-3-270m", "MODEL")
    # Basic structural checks (you don’t need network access if compute stubs data)
    assert result.name
    assert "size_score" in result.__dict__ or hasattr(result, "size_score")
