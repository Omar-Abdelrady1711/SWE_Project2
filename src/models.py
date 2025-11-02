from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Literal, TypedDict, Optional, cast

# Keep the simple Category literal used across the project
Category = Literal["MODEL", "DATASET", "CODE"]


class SizeScore(TypedDict, total=False):
    raspberry_pi: float
    jetson_nano: float
    desktop_pc: float
    aws_server: float


@dataclass
class MetricResult:
    """Canonical, tolerant MetricResult used by orchestrator and metrics.

    To make it safe for partial metric implementations the fields are
    given reasonable defaults so a metric may populate only the fields
    it cares about.
    """
    name: str = ""
    category: Category = "MODEL"

    net_score: float = 0.0
    net_score_latency: int = 0

    ramp_up_time: float = 0.0
    ramp_up_time_latency: int = 0

    bus_factor: float = 0.0
    bus_factor_latency: int = 0

    performance_claims: float = 0.0
    performance_claims_latency: int = 0

    license: float = 0.0
    license_latency: int = 0

    size_score: SizeScore = field(default_factory=lambda: {
        "raspberry_pi": 0.0,
        "jetson_nano": 0.0,
        "desktop_pc": 0.0,
        "aws_server": 0.0,
    })
    size_score_latency: int = 0

    dataset_and_code_score: float = 0.0
    dataset_and_code_score_latency: int = 0

    dataset_quality: float = 0.0
    dataset_quality_latency: int = 0

    code_quality: float = 0.0
    code_quality_latency: int = 0

    extras: Dict[str, float] = field(default_factory=dict)

    # Allow a caller to explicitly mark missing values
    def merged_with(self, other: "MetricResult") -> "MetricResult":
        """Merge another MetricResult into this one, preferring non-default
        values from `other`. This is a simple helper used by the orchestrator.
        """
        out = MetricResult()
        out.name = other.name or self.name
        out.category = other.category or self.category
        # numeric fields: take max value where appropriate or prefer other
        out.net_score = other.net_score or self.net_score
        out.net_score_latency = other.net_score_latency or self.net_score_latency
        out.ramp_up_time = other.ramp_up_time or self.ramp_up_time
        out.ramp_up_time_latency = other.ramp_up_time_latency or self.ramp_up_time_latency
        out.bus_factor = other.bus_factor or self.bus_factor
        out.bus_factor_latency = other.bus_factor_latency or self.bus_factor_latency
        out.performance_claims = other.performance_claims or self.performance_claims
        out.performance_claims_latency = other.performance_claims_latency or self.performance_claims_latency
        out.license = other.license or self.license
        out.license_latency = other.license_latency or self.license_latency
        # merge size_score dicts
        ss = dict(self.size_score)
        ss.update(other.size_score or {})
        # `ss` is a plain dict[str, float]; cast to SizeScore so static
        # type-checkers accept the assignment to the TypedDict field.
        out.size_score = cast(SizeScore, ss)
        out.size_score_latency = other.size_score_latency or self.size_score_latency
        out.dataset_and_code_score = other.dataset_and_code_score or self.dataset_and_code_score
        out.dataset_and_code_score_latency = other.dataset_and_code_score_latency or self.dataset_and_code_score_latency
        out.dataset_quality = other.dataset_quality or self.dataset_quality
        out.dataset_quality_latency = other.dataset_quality_latency or self.dataset_quality_latency
        out.code_quality = other.code_quality or self.code_quality
        out.code_quality_latency = other.code_quality_latency or self.code_quality_latency
        # shallow merge extras
        e = dict(self.extras)
        e.update(other.extras or {})
        out.extras = e
        return out
