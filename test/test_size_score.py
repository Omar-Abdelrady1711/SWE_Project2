from acemcli.metrics.size_score import SizeScoreMetric

def test_supports_size_metric_model_url():
    m = SizeScoreMetric()
    assert m.supports("https://huggingface.co/google/gemma-3-270m", "MODEL")
