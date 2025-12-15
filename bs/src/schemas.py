from pydantic import BaseModel, ConfigDict, HttpUrl
from typing import List, Optional, Dict, Any
from enum import Enum

class ArtifactType(str, Enum):
    model = "model"
    dataset = "dataset"
    code = "code"

#yes
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
    url: Optional[str] = None  # Add URL field

class ArtifactQueryIn(BaseModel):
    name: str
    types: Optional[List[ArtifactType]] = None

class ArtifactDataIn(BaseModel):
    url: HttpUrl

class ArtifactOut(BaseModel):
    metadata: ArtifactMetadataOut
    data: Dict[str, Any]   # <-- IMPORTANT

class LineageEdge(BaseModel):
    parent_id: str
    child_id: str

class LineageGraphOut(BaseModel):
    id: str
    type: ArtifactType
    name: str
    ancestors: List[str]
    edges: List[LineageEdge]

class LineageUpdateIn(BaseModel):
    parents: List[str]

class SizeScoreOut(BaseModel):
    raspberry_pi: float
    jetson_nano: float
    desktop_pc: float
    aws_server: float

class ModelRatingOut(BaseModel):
    name: str
    category: str

    net_score: float
    net_score_latency: float
    ramp_up_time: float
    ramp_up_time_latency: float
    bus_factor: float
    bus_factor_latency: float
    performance_claims: float
    performance_claims_latency: float
    license: float
    license_latency: float
    dataset_and_code_score: float
    dataset_and_code_score_latency: float
    dataset_quality: float
    dataset_quality_latency: float
    code_quality: float
    code_quality_latency: float
    reproducibility: float
    reproducibility_latency: float
    reviewedness: float
    reviewedness_latency: float
    tree_score: float
    tree_score_latency: float
    size_score: SizeScoreOut
    size_score_latency: float

