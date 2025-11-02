from __future__ import annotations
import logging
from typing import List
from models import MetricResult
from metrics.base import supported_metrics
from utils.parse import infer_category_from_url

logger = logging.getLogger(__name__)


def _compute_net_score(mr: MetricResult) -> float:
	fields = [
		mr.ramp_up_time,
		mr.bus_factor,
		mr.performance_claims,
		mr.license,
		mr.dataset_and_code_score,
		mr.dataset_quality,
		mr.code_quality,
	]
	vals = [v for v in fields if isinstance(v, (int, float))]
	if not vals:
		return 0.0
	return sum(vals) / len(vals)


def score_urls(urls: List[str]) -> List[MetricResult]:
	"""Score a list of URLs using registered metrics. Returns a list of
	merged MetricResult objects (one per URL).
	"""
	out: List[MetricResult] = []
	for url in urls:
		cat = infer_category_from_url(url)
		mets = supported_metrics(url, cat)
		merged: MetricResult | None = None
		for m in mets:
			try:
				r = m.compute(url, cat)
				if merged is None:
					merged = r
				else:
					merged = merged.merged_with(r)
			except Exception as e:
				logger.exception("Metric %s failed for %s: %s", getattr(m, 'name', repr(m)), url, e)
		if merged is None:
			# create a blank result
			merged = MetricResult(name=url, category=cat)
		merged.net_score = _compute_net_score(merged)
		out.append(merged)
	return out

