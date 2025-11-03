from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

DATABASE_URL = "sqlite:///./registry.db"   # local file next to bs/
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()

class ArtifactModel(Base):
    __tablename__ = "artifacts"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    type = Column(String, nullable=False)
    description = Column(String, nullable=True)

def init_db() -> None:
    Base.metadata.create_all(bind=engine)

# <-- THIS is what your router imports
def get_session() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
