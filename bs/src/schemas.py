from pydantic import BaseModel, ConfigDict, HttpUrl
from typing import List, Optional


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
