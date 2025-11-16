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