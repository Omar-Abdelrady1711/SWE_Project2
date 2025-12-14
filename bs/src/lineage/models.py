import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from bs.src.models_db import Base


class LineageEdge(Base):
    __tablename__ = "model_lineage_edges"
    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(String, nullable=False, index=True)
    parent_model_id = Column(String, nullable=False, index=True)
    relation = Column(String, nullable=True)
    meta = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def upsert_edges(session, model_id: str, parents: list[dict]):
    """Replace existing parents for model_id with provided parents list.

    Each parent dict should contain keys: 'parent_id' and optional 'relation' and 'metadata'.
    """
    # delete existing edges for model
    session.query(LineageEdge).filter(LineageEdge.model_id == model_id).delete()
    for p in parents:
        pe = LineageEdge(
            model_id=model_id,
            parent_model_id=str(p.get("parent_id")),
            relation=p.get("relation"),
            meta=json.dumps(p.get("metadata")) if p.get("metadata") is not None else None,
        )
        session.add(pe)
    session.commit()


def get_parents(session, model_id: str) -> list[dict]:
    rows = session.query(LineageEdge).filter(LineageEdge.model_id == model_id).all()
    out = []
    for r in rows:
        md = None
        if r.meta:
            try:
                md = json.loads(r.meta)
            except Exception:
                md = None
        out.append({"parent_id": r.parent_model_id, "relation": r.relation, "metadata": md})
    return out
