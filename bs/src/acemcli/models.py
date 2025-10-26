from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Literal, TypedDict

Category = Literal["MODEL", "DATASET", "CODE"]

class SizeScore(TypedDict):
    raspberry_pi: float
    jetson_nano: float
    desktop_pc: float
    aws_server: float

@dataclass
class MetricResult:
    name: str
    category: Category

    net_score: float
    net_score_latency: int

    ramp_up_time: float
    ramp_up_time_latency: int

    bus_factor: float
    bus_factor_latency: int

    performance_claims: float
    performance_claims_latency: int

    license: float
    license_latency: int

    size_score: SizeScore
    size_score_latency: int

    dataset_and_code_score: float
    dataset_and_code_score_latency: int

    dataset_quality: float
    dataset_quality_latency: int

    code_quality: float
    code_quality_latency: int

    extras: Dict[str, float] = field(default_factory=dict)
