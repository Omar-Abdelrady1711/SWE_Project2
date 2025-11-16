from typing import Generator
from sqlmodel import create_engine, Session
from sqlmodel import SQLModel
import os

DATABASE_URL = os.environ.get("BACKEND_DATABASE_URL", "sqlite:///backend.db")

engine = create_engine(DATABASE_URL, echo=False)

def init_db() -> None:
    SQLModel.metadata.create_all(engine)

def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
