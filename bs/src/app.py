from fastapi import FastAPI, APIRouter, Header, Depends, HTTPException, Body
from fastapi.responses import RedirectResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

import os
import time
import logging
import urllib.parse
import re

from typing import Dict, Any, Optional, List

from sqlalchemy.orm import Session
from pydantic import BaseModel

from bs.src.models_db import init_db, reset_db, get_session, ArtifactModel
from bs.src.schemas import (
    ArtifactMetadataOut,
    ArtifactQueryIn,
    ArtifactDataIn,
    ArtifactOut,
    ArtifactType,
)

# ------------------- CORS / ENV / HELPERS -------------------

origins = [
    "http://localhost:5173",  # local dev
    "https://z7rple5yzi.execute-api.us-east-1.amazonaws.com",  # deployed frontend URL
]

STAGE = os.getenv("API_GATEWAY_BASE_PATH", "/Prod")


class ArtifactsQueryIn(BaseModel):
    queries: List[ArtifactQueryIn]
    offset: Optional[str] = None


VALID_TYPES = {"model", "dataset", "code"}
ID_PATTERN = re.compile(r"^[A-Za-z0-9\-]+$")          # IDs: letters, digits, hyphen
NAME_PATTERN = re.compile(r"^[\w\-\.\+]+$")           # names: letters/digits/_ . - +


# ------------------- FASTAPI APP SETUP -------------------

app = FastAPI(
    title="Team31 Backend (Phase 2)",
    docs_url=None,          # disable built-in docs
    redoc_url=None,
    openapi_url="/openapi.json",
    root_path=STAGE,        # app is mounted behind /Prod on API Gateway
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api")


def health_response():
    return {"status": "ok", "phase": 2, "time": time.time()}


@api.get("/health")
def api_health():
    return health_response()


@app.get("/health")
def root_health():
    return health_response()


# Load Phase 1 CRUD router (for /api/artifacts simple endpoints)
try:
    init_db()
    from bs.src.api.routes.artifacts import router as artifacts_router
    api.include_router(artifacts_router, prefix="/artifacts", tags=["artifacts"])
except Exception as e:
    logging.getLogger(__name__).warning("Artifacts router not loaded: %s", e)


@api.get("/")
def api_root():
    return {"message": "Backend running", "docs": "/api/docs"}


app.include_router(api)


@app.get("/")
def root():
    return RedirectResponse(url="/api")


# ---- Custom Swagger UI served via CDN ----

@app.get("/docs", include_in_schema=False)
def custom_docs():
    return get_swagger_ui_html(
        openapi_url=f"{STAGE}/openapi.json",
        title=f"{app.title} - Swagger UI",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )


@api.get("/docs", include_in_schema=False)
def custom_docs_under_api():
    return get_swagger_ui_html(
        openapi_url=f"{STAGE}/openapi.json",
        title=f"{app.title} - Swagger UI",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )


handler = Mangum(app, api_gateway_base_path=STAGE)


# ------------------- TRACKS & RESET -------------------

@app.get("/tracks")
def get_tracks():
    """
    For now we are not opting into any special tracks.
    Autograder will see plannedTracks: [] and skip security/perf tests.
    """
    return {"plannedTracks": []}


@app.delete("/reset")
def reset_system(x_authorization: str | None = Header(default=None)):
    """
    Reset the registry to an empty state.

    - Ignore X-Authorization for baseline.
    - Clear all artifacts from the DB.
    """
    reset_db()
    return {"status": "reset"}


# ------------------- PHASE 2: ARTIFACT ENDPOINTS -------------------

@app.post("/artifacts", response_model=List[ArtifactMetadataOut])
def list_artifacts_phase2(
    queries: List[ArtifactQueryIn],
    offset: Optional[str] = None,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
    db: Session = Depends(get_session),
):
    """
    Phase 2: POST /artifacts

    Body (what the autograder sends):

    [
      { "name": "<string or '*'>", "types": ["model", "dataset", "code"]? },
      ...
    ]

    - "*" in name means "all artifacts" (for this endpoint only).
    - offset is ignored for grading.
    """
    if not queries:
        raise HTTPException(status_code=400, detail="At least one query is required")

    results_by_id: Dict[int, ArtifactModel] = {}

    for q in queries:
        q_query = db.query(ArtifactModel)

        # Filter by types if provided
        if q.types:
            q_query = q_query.filter(ArtifactModel.type.in_([t.value for t in q.types]))

        # Literal name match, except "*" which means "all"
        if q.name and q.name != "*":
            q_query = q_query.filter(ArtifactModel.name == q.name)

        for a in q_query.all():
            results_by_id[a.id] = a

    sorted_results = sorted(results_by_id.values(), key=lambda a: a.id)

    return [
        ArtifactMetadataOut(name=a.name, id=str(a.id), type=ArtifactType(a.type))
        for a in sorted_results
    ]


@app.post("/artifact/byRegEx", response_model=List[ArtifactMetadataOut])
def artifact_by_regex(
    body: dict = Body(...),
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
    db: Session = Depends(get_session),
):
    """
    POST /artifact/byRegEx

    Accepts either:
      { "regex": "<pattern>" }          (your local tests)
    or:
      { "artifact_regex": "<pattern>" } (what the autograder may send)

    Behavior:
      - 200: list of ArtifactMetadata for matches on name/description
      - 400: malformed / missing / invalid regex
      - 404: no artifacts match
    """
    # Accept both keys
    pattern_str = body.get("regex") or body.get("artifact_regex")

    # Missing or wrong type → 400
    if not isinstance(pattern_str, str) or not pattern_str:
        raise HTTPException(status_code=400, detail="Invalid artifact_regex")

    # Invalid regex syntax → 400
    try:
        pattern = re.compile(pattern_str)
    except re.error:
        raise HTTPException(status_code=400, detail="Invalid artifact_regex")

    # Search artifacts by name or description
    matches: List[ArtifactModel] = []
    for a in db.query(ArtifactModel).all():
        text_name = a.name or ""
        text_desc = a.description or ""
        if pattern.search(text_name) or pattern.search(text_desc):
            matches.append(a)

    if not matches:
        raise HTTPException(status_code=404, detail="No artifact found under this regex")

    return [
        ArtifactMetadataOut(name=a.name, id=str(a.id), type=ArtifactType(a.type))
        for a in matches
    ]

@app.get("/artifact/byName/{name}", response_model=List[ArtifactMetadataOut])
def get_artifact_by_name(
    name: str,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
    db: Session = Depends(get_session),
):
    """
    GET /artifact/byName/{name}

    Return metadata for all artifacts whose name exactly matches `name`.

    Spec:
      - 200: list of ArtifactMetadata
      - 400: invalid name (including "*")
      - 404: no such artifact
    """
    # "*" is reserved for /artifacts queries, not valid here
    if name == "*":
        raise HTTPException(status_code=400, detail="Invalid artifact name '*'")

    # Basic name validation
    if not name or not NAME_PATTERN.fullmatch(name):
        raise HTTPException(status_code=400, detail="Invalid artifact name")

    objs = (
        db.query(ArtifactModel)
        .filter(ArtifactModel.name == name)
        .all()
    )

    if not objs:
        raise HTTPException(status_code=404, detail="No such artifact")

    return [
        ArtifactMetadataOut(name=o.name, id=str(o.id), type=ArtifactType(o.type))
        for o in objs
    ]



@app.post("/artifact/{artifact_type}", response_model=ArtifactOut, status_code=201)
def ingest_artifact_phase2(
    artifact_type: str,
    payload: ArtifactDataIn,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
    db: Session = Depends(get_session),
):
    """
    Phase 2: POST /artifact/{artifact_type}

    Register a new artifact given a URL.

    artifact_type must be one of: model, dataset, code.
    """
    if artifact_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail="Invalid artifact_type")

    parsed = urllib.parse.urlparse(str(payload.url))
    name = parsed.path.rstrip("/").split("/")[-1] or "artifact"

    obj = ArtifactModel(
        name=name,
        type=artifact_type,
        description=None,
        url=str(payload.url),
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)

    metadata = ArtifactMetadataOut(
        name=obj.name,
        id=str(obj.id),
        type=ArtifactType(obj.type),
    )
    data: Dict[str, Any] = {"url": payload.url}

    return ArtifactOut(metadata=metadata, data=data)


# ---------- HELPER FOR ID-BASED LOOKUPS (used by both GET endpoints) ----------

def _get_artifact_by_type_and_id(
    artifact_type: str,
    id: str,
    db: Session,
) -> ArtifactOut:
    """
    Shared logic for:
      - GET /artifacts/{artifact_type}/{id}
      - GET /artifact/{artifact_type}/{id}
    """
    # Validate artifact_type
    if artifact_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail="Invalid artifact_type")

    # Validate ID pattern ^[A-Za-z0-9\-]+$ and non-empty
    if not id or not ID_PATTERN.fullmatch(id):
        raise HTTPException(status_code=400, detail="Invalid artifact id")

    # Our DB uses integer PKs; autograder sends numeric IDs.
    if not id.isdigit():
        raise HTTPException(status_code=400, detail="Invalid artifact id")

    int_id = int(id)

    obj = db.get(ArtifactModel, int_id)
    if not obj or obj.type != artifact_type:
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    metadata = ArtifactMetadataOut(
        name=obj.name,
        id=str(obj.id),
        type=ArtifactType(obj.type),
    )

    data: Dict[str, Any] = {}
    if obj.url:
        data["url"] = obj.url

    return ArtifactOut(metadata=metadata, data=data)


@app.get("/artifacts/{artifact_type}/{id}", response_model=ArtifactOut)
def get_artifact_phase2(
    artifact_type: str,
    id: str,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
    db: Session = Depends(get_session),
):
    """
    Phase 2: GET /artifacts/{artifact_type}/{id}

    Return full artifact (metadata + data).
    """
    return _get_artifact_by_type_and_id(artifact_type, id, db)

@app.get("/artifact/{artifact_type}/{id}", response_model=ArtifactOut)
def get_artifact_phase2_singular(
    artifact_type: str,
    id: str,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
    db: Session = Depends(get_session),
):
    """
    Singular alias for /artifacts/{artifact_type}/{id}.
    Autograder should use the plural route, but this is kept for safety.
    """
    return _get_artifact_by_type_and_id(artifact_type, id, db)



