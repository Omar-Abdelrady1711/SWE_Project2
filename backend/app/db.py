from typing import Generator
from sqlmodel import create_engine, Session
from sqlmodel import SQLModel
# ensure models are imported so SQLModel metadata is populated before create_all
from . import models  # noqa: F401
import os

DATABASE_URL = os.environ.get("BACKEND_DATABASE_URL", "sqlite:///backend.db")

engine = create_engine(DATABASE_URL, echo=False)

def init_db() -> None:
    SQLModel.metadata.create_all(engine)

def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
