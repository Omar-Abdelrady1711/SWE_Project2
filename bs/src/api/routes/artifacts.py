# api/routes/artifacts.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.schemas import Artifact, ArtifactCreate
from src.models_db import ArtifactModel, get_session

router = APIRouter()

@router.post("", response_model=Artifact, status_code=201)
def create_artifact(payload: ArtifactCreate, db: Session = Depends(get_session)):
    obj = ArtifactModel(name=payload.name, type=payload.type, description=payload.description)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.get("/{artifact_id}", response_model=Artifact)
def get_artifact(artifact_id: int, db: Session = Depends(get_session)):
    obj = db.get(ArtifactModel, artifact_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Not found")
    return obj

@router.get("", response_model=list[Artifact])
def list_artifacts(db: Session = Depends(get_session)):
    return db.query(ArtifactModel).all()

@router.put("/{artifact_id}", response_model=Artifact)
def update_artifact(artifact_id: int, payload: ArtifactCreate, db: Session = Depends(get_session)):
    obj = db.get(ArtifactModel, artifact_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Not found")
    obj.name, obj.type, obj.description = payload.name, payload.type, payload.description
    db.commit()
    db.refresh(obj)
    return obj

@router.delete("/{artifact_id}", status_code=204)
def delete_artifact(artifact_id: int, db: Session = Depends(get_session)):
    obj = db.get(ArtifactModel, artifact_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(obj)
    db.commit()
    return None
