from fastapi import FastAPI, APIRouter, Header, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from fastapi.openapi.docs import get_swagger_ui_html
from mangum import Mangum
import os, time, logging, urllib.parse
from typing import Dict, Any, Optional, List
from fastapi.middleware.cors import CORSMiddleware
import re

from sqlalchemy.orm import Session

from bs.src.models_db import init_db, reset_db, get_session, ArtifactModel
from bs.src.schemas import (
    ArtifactMetadataOut,
    ArtifactQueryIn,
    ArtifactDataIn,
    ArtifactOut,
)

ID_PATTERN = re.compile(r"^[a-zA-Z0-9\-]+$")

# Define which frontend origins are allowed to call this backend
origins = [
    "http://localhost:5173",                #local dev
    "https://z7rple5yzi.execute-api.us-east-1.amazonaws.com"   # deployed frontend URL
]

STAGE = os.getenv("API_GATEWAY_BASE_PATH", "/Prod")

from pydantic import BaseModel

class ArtifactRegExIn(BaseModel):
    regex: str
    
app = FastAPI(
    title="Team31 Backend (Phase 2)",
    docs_url=None,                        # <-- disable built-in docs
    redoc_url=None,
    openapi_url="/openapi.json",  # <-- OpenAPI served under the stage
    root_path=STAGE,                      # <-- tell FastAPI it's mounted at /Prod
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          # allowed domains
    allow_credentials=True,         # allow cookies / auth headers if needed
    allow_methods=["*"],            # allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],            # allow all headers (Authorization, Content-Type, etc.)
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

# (safe-load your DB router exactly as you had)
try:
    from bs.src.models_db import init_db
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

# ---- Custom Swagger UI served via CDN (avoids API GW static routes) ----
@app.get("/docs", include_in_schema=False)
def custom_docs():
    return get_swagger_ui_html(
        openapi_url=f"{STAGE}/openapi.json",
        title=f"{app.title} - Swagger UI",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )
# (If you prefer under the API prefix too:)
@api.get("/docs", include_in_schema=False)
def custom_docs_under_api():
    return get_swagger_ui_html(
        openapi_url=f"{STAGE}/openapi.json",
        title=f"{app.title} - Swagger UI",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )

handler = Mangum(app, api_gateway_base_path=STAGE)

@app.get("/tracks")
def get_tracks():
    # We are not doing any special track yet, so just return empty list.
    # (If later you do Access control or Performance, add them here.)
    return {"plannedTracks": []}


@app.delete("/reset")
def reset_system(x_authorization: str | None = Header(default=None)):
    """
    Reset the registry to an empty state.

    - Ignore X-Authorization for now (we're not doing access-control track).
    - Clear all artifacts from the DB.
    """
    reset_db()
    return {"status": "reset"}

# -------- Phase 2: /artifacts and /artifact endpoints --------
@app.post("/artifacts", response_model=List[ArtifactMetadataOut])
def list_artifacts_phase2(
    queries: List[ArtifactQueryIn],
    offset: Optional[str] = Query(default=None),
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
    db: Session = Depends(get_session),
):
    """
    Phase 2: POST /artifacts

    - `queries` is an array of ArtifactQuery objects (name + optional types).
    - `name` is a literal string; "*" means "all artifacts".
    - We ignore offset and X-Authorization for grading.
    """
    if not queries:
        raise HTTPException(status_code=400, detail="At least one query is required")

    # Union of results across all queries, deduped by id
    results_by_id: dict[int, ArtifactModel] = {}

    for q in queries:
        q_query = db.query(ArtifactModel)

        # Filter by types if provided
        if q.types:
            q_query = q_query.filter(ArtifactModel.type.in_(q.types))

        # Literal name match (except for "*")
        if q.name and q.name != "*":
            q_query = q_query.filter(ArtifactModel.name == q.name)

        for a in q_query.all():
            results_by_id[a.id] = a

    # Stable ordering
    sorted_results = sorted(results_by_id.values(), key=lambda a: a.id)

    return [
        ArtifactMetadataOut(name=a.name, id=str(a.id), type=a.type)
        for a in sorted_results
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
    """
    if artifact_type not in {"model", "dataset", "code"}:
        raise HTTPException(status_code=400, detail="Invalid artifact_type")

    # Derive a simple name from the URL (last path component)
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

    metadata = ArtifactMetadataOut(name=obj.name, id=str(obj.id), type=obj.type)
    data = {"url": payload.url}

    return ArtifactOut(metadata=metadata, data=data)

VALID_TYPES = {"model", "dataset", "code"}


@app.post("/artifact/byRegEx", response_model=List[ArtifactMetadataOut])
def artifact_by_regex(
    payload: ArtifactRegExIn,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
    db: Session = Depends(get_session),
):
    """
    POST /artifact/byRegEx

    Search for artifacts whose name or README/description matches the given regex.
    """

    # 1) Empty / whitespace-only regex ⇒ 400 (invalid)
    if not payload.regex or payload.regex.strip() == "":
        raise HTTPException(status_code=400, detail="Invalid artifact_regex")

    # 2) Malformed regex ⇒ 400
    try:
        pattern = re.compile(payload.regex)
    except re.error:
        raise HTTPException(status_code=400, detail="Invalid artifact_regex")

    # 3) Search over name + description (+ readme_content if present)
    matches: list[ArtifactModel] = []
    for a in db.query(ArtifactModel).all():
        text_name = a.name or ""
        text_desc = getattr(a, "description", "") or ""
        text_readme = getattr(a, "readme_content", "") or ""
        haystack = f"{text_name}\n{text_desc}\n{text_readme}"
        if pattern.search(haystack):
            matches.append(a)

    # 4) No matches ⇒ 404
    if not matches:
        raise HTTPException(status_code=404, detail="No artifact found under this regex")

    # 5) At least one match ⇒ 200 + list of ArtifactMetadata
    return [
        ArtifactMetadataOut(name=a.name, id=str(a.id), type=a.type)
        for a in matches
    ]


@app.get("/artifacts/{artifact_type}/{id}", response_model=ArtifactOut)
def get_artifact_phase2(
    artifact_type: str,
    id: str,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
    db: Session = Depends(get_session),
):
    """
    Phase 2: GET /artifacts/{artifact_type}/{id}

    Return full artifact (metadata + data.url).
    """

    # 1) Validate artifact_type
    if artifact_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail="Invalid artifact_type")

    # 2) Validate artifact_id format
    if not id or not ID_PATTERN.match(id):
        raise HTTPException(status_code=400, detail="Invalid artifact_id")

    # our DB uses integer primary key, but the spec's ArtifactID is a string.
    # autograder uses numeric strings like "3847247294", so we parse as int.
    try:
        int_id = int(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid artifact_id")

    # 3) Look up artifact
    obj = db.get(ArtifactModel, int_id)
    if not obj:
        # valid id format, but doesn't exist => 404
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    # 4) If id exists but type doesn't match ⇒ 400
    if obj.type != artifact_type:
        raise HTTPException(status_code=400, detail="artifact_type does not match artifact")

    # 5) Build response
    metadata = ArtifactMetadataOut(name=obj.name, id=str(obj.id), type=obj.type)
    data = {"url": obj.url} if obj.url else {}

    return ArtifactOut(metadata=metadata, data=data)

@app.get("/artifact/byName/{name}", response_model=List[ArtifactMetadataOut])
def get_artifact_by_name(
    name: str,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
    db: Session = Depends(get_session),
):
    """
    GET /artifact/byName/{name}

    Return metadata for all artifacts whose name exactly matches `name`.
    """
    objs = (
        db.query(ArtifactModel)
        .filter(ArtifactModel.name == name)
        .all()
    )

    if not objs:
        # Spec: "404: No such artifact."
        raise HTTPException(status_code=404, detail="No such artifact")

    return [
        ArtifactMetadataOut(name=o.name, id=str(o.id), type=o.type)
        for o in objs
    ]

