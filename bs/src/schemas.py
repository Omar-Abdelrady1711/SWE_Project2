from pydantic import BaseModel, ConfigDict, HttpUrl
from typing import List, Optional, Dict, Any
from enum import Enum

class ArtifactType(str, Enum):
    model = "model"
    dataset = "dataset"
    code = "code"

class ArtifactBase(BaseModel):
    name: str
    type: ArtifactType
    description: Optional[str] = None

class ArtifactCreate(ArtifactBase):
    pass

class Artifact(BaseModel):
    id: int
    name: str
    type: ArtifactType
    description: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class ArtifactMetadataOut(BaseModel):
    name: str
    id: str
    type: ArtifactType

class ArtifactQueryIn(BaseModel):
    name: str
    types: Optional[List[ArtifactType]] = None

class ArtifactDataIn(BaseModel):
    url: HttpUrl

class ArtifactOut(BaseModel):
    metadata: ArtifactMetadataOut
    data: Dict[str, Any]   # <-- IMPORTANT

class SizeScoreOut(BaseModel):
    raspberry_pi: float
    jetson_nano: float
    desktop_pc: float
    aws_server: float

class ModelRatingOut(BaseModel):
    name: str
    category: str

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
    dataset_and_code_score: float
    dataset_and_code_score_latency: int
    dataset_quality: float
    dataset_quality_latency: int
    code_quality: float
    code_quality_latency: int

    reproducibility: float
    reproducibility_latency: int
    reviewedness: float
    reviewedness_latency: int
    tree_score: float
    tree_score_latency: int

    size_score: SizeScoreOut
    size_score_latency: int

