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
