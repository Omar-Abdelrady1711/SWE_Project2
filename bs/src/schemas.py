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
