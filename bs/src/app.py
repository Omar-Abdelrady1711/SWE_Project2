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

# Define which frontend origins are allowed to call this backend
origins = [
    "http://localhost:5173",                #local dev
    "https://z7rple5yzi.execute-api.us-east-1.amazonaws.com"   # deployed frontend URL
]

STAGE = os.getenv("API_GATEWAY_BASE_PATH", "/Prod")

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

    - `queries` is an array of ArtifactQueryIn objects.
    - `name` is treated as a REGEX over artifact name/description.
    - To list everything, the autograder will send: [{"name": "*"}].
    - We ignore offset and X-Authorization for now.
    """
    if not queries:
        raise HTTPException(status_code=400, detail="At least one query is required")

    # For Phase 2, just honor the first query
    q = queries[0]

    # Start with type filtering in the DB
    query = db.query(ArtifactModel)
    if q.types:
        query = query.filter(ArtifactModel.type.in_(q.types))

    all_candidates = query.all()

    # If name is "*" or empty → no regex filtering, just return everything (within types)
    if not q.name or q.name == "*":
        matched = all_candidates
    else:
        # Treat q.name as a regular expression over name / description
        try:
            pattern = re.compile(q.name)
        except re.error:
            # If they send an invalid regex, fall back to literal match
            pattern = re.compile(re.escape(q.name))

        matched = []
        for a in all_candidates:
            text_name = a.name or ""
            text_desc = a.description or ""
            if pattern.search(text_name) or pattern.search(text_desc):
                matched.append(a)

    return [
        ArtifactMetadataOut(name=a.name, id=str(a.id), type=a.type)
        for a in matched
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
    try:
        int_id = int(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid artifact id")

    obj = db.get(ArtifactModel, int_id)
    if not obj or obj.type != artifact_type:
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    metadata = ArtifactMetadataOut(name=obj.name, id=str(obj.id), type=obj.type)
    data = {"url": obj.url} if obj.url else {}

    return ArtifactOut(metadata=metadata, data=data)

@app.get("/artifact/{artifact_type}/{id}", response_model=ArtifactOut)
def get_artifact_phase2_singular(
    artifact_type: str,
    id: str,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
    db: Session = Depends(get_session),
):
    """
    Phase 2: GET /artifact/{artifact_type}/{id}
    Return full artifact (metadata + data.url).
    """
    try:
        int_id = int(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid artifact id")

    obj = db.get(ArtifactModel, int_id)
    if not obj or obj.type != artifact_type:
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    metadata = ArtifactMetadataOut(name=obj.name, id=str(obj.id), type=obj.type)
    data = {"url": obj.url} if obj.url else {}

    return ArtifactOut(metadata=metadata, data=data)

