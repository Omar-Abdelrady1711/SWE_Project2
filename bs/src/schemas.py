from pydantic import BaseModel, ConfigDict, HttpUrl
from typing import List, Optional, Literal
from pydantic import BaseModel, ConfigDict


class ArtifactBase(BaseModel):
    name: str
    type: str
    description: str | None = None

class ArtifactCreate(ArtifactBase):
    pass

class Artifact(ArtifactBase):
    id: int
    # replaces orm_mode=True
    model_config = ConfigDict(from_attributes=True)

class ArtifactMetadataOut(BaseModel):
    name: str
    id: str
    type: str

class ArtifactQueryIn(BaseModel):
    name: str
    types: Optional[List[str]] = None

class ArtifactDataIn(BaseModel):
    url: HttpUrl

class ArtifactOut(BaseModel):
    metadata: ArtifactMetadataOut
    data: dict[str, HttpUrl]

class SizeScoreModel(BaseModel):
    raspberry_pi: float
    jetson_nano: float
    desktop_pc: float
    aws_server: float

class ModelRating(BaseModel):
    name: str
    category: str  # or Literal["MODEL"]

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

    tree_score: float
    tree_score_latency: float

    reproducibility: float
    reproducibility_latency: float

    reviewedness: float
    reviewedness_latency: float

    size_score: SizeScoreModel
    size_score_latency: float

    model_config = ConfigDict(from_attributes=True)
