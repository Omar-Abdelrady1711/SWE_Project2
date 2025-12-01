# bs/src/models_db.py
import os
from pathlib import Path
from sqlalchemy import Column, Integer, String, DateTime, Boolean, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import datetime

# Writable on AWS Lambda
DB_DIR = Path("/tmp")
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "registry.db"

# Allow override via env if you later move to RDS/other DB
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()

class ArtifactModel(Base):
    __tablename__ = "artifacts"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    type = Column(String, nullable=False)
    description = Column(String, nullable=True)
    url = Column(String, nullable=True)

class UserModel(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="user")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

def init_db() -> None:
    # Safe to call more than once; creates table if missing
    Base.metadata.create_all(bind=engine)

def get_session() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def reset_db() -> None:
    """
    Drop and recreate all tables.

    Used by the /reset endpoint to wipe all artifacts so the system
    is in a clean state for the autograder.
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

