from src.metrics.dataset_quality import DatasetQualityMetric

def test_supports_dataset_quality_dataset_url():
    m = DatasetQualityMetric()
    assert m.supports("https://huggingface.co/datasets/squad", "DATASET")
