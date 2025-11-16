from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime


class Device(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    mqtt_client_id: Optional[str] = None
    location: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FishProfile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    preferred_temp_c: Optional[float] = None
    preferred_ph: Optional[float] = None
    notes: Optional[str] = None


class SensorReading(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    device_id: Optional[int] = None
    sensor_type: str
    value: str
    ts: datetime = Field(default_factory=datetime.utcnow)


class Schedule(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    cron: Optional[str] = None
    payload: Optional[str] = None


class Config(SQLModel, table=True):
    key: str = Field(primary_key=True)
    value: Optional[str] = None
