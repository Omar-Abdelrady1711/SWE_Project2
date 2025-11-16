from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlmodel import select
from .db import get_session
from .models import Device, FishProfile, SensorReading

router = APIRouter(prefix="/api", tags=["api"])


@router.post("/devices/", response_model=Device)
def create_device(device: Device, session=Depends(get_session)):
    session.add(device)
    session.commit()
    session.refresh(device)
    return device


@router.get("/devices/", response_model=List[Device])
def list_devices(session=Depends(get_session)):
    stmt = select(Device)
    results = session.exec(stmt).all()
    return results


@router.get("/devices/{device_id}", response_model=Device)
def get_device(device_id: int, session=Depends(get_session)):
    device = session.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.delete("/devices/{device_id}")
def delete_device(device_id: int, session=Depends(get_session)):
    device = session.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    session.delete(device)
    session.commit()
    return {"ok": True}


@router.post("/readings/", response_model=SensorReading)
def create_reading(reading: SensorReading, session=Depends(get_session)):
    session.add(reading)
    session.commit()
    session.refresh(reading)
    return reading


@router.get("/readings/", response_model=List[SensorReading])
def list_readings(limit: int = 100, session=Depends(get_session)):
    stmt = select(SensorReading).limit(limit)
    return session.exec(stmt).all()


@router.post("/fish_profiles/", response_model=FishProfile)
def create_fish_profile(profile: FishProfile, session=Depends(get_session)):
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile


@router.get("/fish_profiles/", response_model=List[FishProfile])
def list_fish_profiles(session=Depends(get_session)):
    stmt = select(FishProfile)
    return session.exec(stmt).all()
