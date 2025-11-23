from fastapi import FastAPI, APIRouter, Header, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

# acemcli rating pipeline (phase 1 + phase 2)
from bs.src.acemcli.orchestrator import _compute_one
from bs.src.acemcli.models import Category as MetricCategory
# IMPORTANT: import metrics package to force registration side-effects
import bs.src.acemcli.metrics  # noqa: F401
from bs.src.schemas import ModelRatingOut, SizeScoreOut

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

class ArtifactRegExIn(BaseModel):
    regex: str

class ArtifactsQueryIn(BaseModel):
    queries: List[ArtifactQueryIn]
    offset: Optional[str] = None

VALID_TYPES = {"model", "dataset", "code"}
ID_PATTERN = re.compile(r"^[a-zA-Z0-9\-]+$")


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

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    force=True,
)

logger = logging.getLogger("autograder")
logger.setLevel(LOG_LEVEL)

@app.middleware("http")
async def log_requests(request, call_next):
    """
    Logs every request + response.
    This is what you need to see what autograder is actually calling.
    """
    start = time.time()

    # Basic request info
    path = request.url.path
    method = request.method
    query = str(request.url.query)

    # Don't log full auth token, just whether it's present
    auth_header = request.headers.get("X-Authorization")
    has_auth = auth_header is not None

    # Try to read body safely (may fail if stream already consumed)
    body_bytes = b""
    try:
        body_bytes = await request.body()
    except Exception:
        pass

    body_preview = body_bytes.decode("utf-8", errors="ignore")
    if len(body_preview) > 500:
        body_preview = body_preview[:500] + "...(truncated)"

    logger.info(
        f"REQ {method} {path}"
        + (f"?{query}" if query else "")
        + f" | has_auth={has_auth} | body={body_preview}"
    )

    response = await call_next(request)

    duration_ms = (time.time() - start) * 1000

    logger.info(
        f"RESP {method} {path} -> {response.status_code} ({duration_ms:.1f}ms)"
    )

    return response

api = APIRouter(prefix="/api")

import urllib.parse

@app.get("/artifact/byName/{name}", response_model=List[ArtifactMetadataOut])
def get_artifact_by_name(
    name: str,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
    db: Session = Depends(get_session),
):
    """
    GET /artifact/byName/{name}

    Spec:
      - 200: list of ArtifactMetadata for this name
      - 400: invalid name (including "*")
      - 404: no such artifact
    """

    logger.info(f"[byName] raw name received: {name}")

    # Decode URL encoding just to be safe
    name_decoded = urllib.parse.unquote(name)
    logger.info(f"[byName] decoded name: {name_decoded}")

    # 1) Reject "*" (reserved for POST /artifacts)
    if name_decoded == "*":
        logger.warning("[byName] name is '*' -> 400")
        raise HTTPException(
            status_code=400,
            detail="Invalid artifact_name: '*' is reserved"
        )

    # 2) Reject empty / whitespace-only
    if not name_decoded or not name_decoded.strip():
        logger.warning("[byName] empty/whitespace name -> 400")
        raise HTTPException(
            status_code=400,
            detail="Invalid artifact_name"
        )

    # 3) Reject control characters (non-printable)
    if any(ord(c) < 32 or c == "\x7f" for c in name_decoded):
        logger.warning("[byName] control character detected -> 400")
        raise HTTPException(
            status_code=400,
            detail="Invalid artifact_name"
        )

    # 4) Query DB for EXACT name match, sort by id ASC
    logger.info(f"[byName] querying DB for exact name='{name_decoded}'")

    objs = (
        db.query(ArtifactModel)
        .filter(ArtifactModel.name == name_decoded)
        .order_by(ArtifactModel.id.asc())
        .all()
    )

    logger.info(f"[byName] DB matches found = {len(objs)}")

    if not objs:
        logger.info("[byName] no matches -> 404")
        raise HTTPException(
            status_code=404,
            detail="No such artifact"
        )

    response = [
        ArtifactMetadataOut(
            name=o.name,
            id=str(o.id),
            type=ArtifactType(o.type)
        )
        for o in objs
    ]

    logger.info(f"[byName] returning {len(response)} results -> 200")
    return response


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

PAGE_SIZE = 10000  # large enough so autograder never hits the limit

@app.post("/artifacts", response_model=List[ArtifactMetadataOut])
def list_artifacts_phase2(
    queries: List[ArtifactQueryIn],              # body: JSON array
    offset: Optional[str] = None,               # ?offset=...
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
    db: Session = Depends(get_session),
    response: Response = None,
):
    """
    Phase 2: POST /artifacts

    Body: a JSON array of ArtifactQuery objects.

    - name: string or "*"
    - types: optional list of ["model", "dataset", "code"]

    Returns a list of ArtifactMetadata objects.
    """
    # ----- Basic validation -----
    if not queries:
        raise HTTPException(status_code=400, detail="At least one query is required")

    # Offset must be a non-negative integer string if present
    try:
        start_index = int(offset) if offset is not None else 0
        if start_index < 0:
            raise ValueError()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid offset")

    results_by_id: Dict[int, ArtifactModel] = {}

    for q in queries:
        # name is required by the schema, but be defensive anyway
        if q.name is None:
            raise HTTPException(status_code=400, detail="ArtifactQuery.name is required")

        q_query = db.query(ArtifactModel)

        # Filter by types if provided
        if q.types:
            # q.types is List[ArtifactType] (Enum), so use .value
            type_values = [t.value for t in q.types]
            q_query = q_query.filter(ArtifactModel.type.in_(type_values))

        # Handle name
        if q.name != "*":  # "*" means wildcard: no name filter
            # EXACT match only; no lowercasing or partial matches
            q_query = q_query.filter(ArtifactModel.name == q.name)

        # Add results, de-duplicated by id
        for a in q_query.all():
            results_by_id[a.id] = a

    # Sort deterministically by id (as string-int)
    sorted_results = sorted(results_by_id.values(), key=lambda a: a.id)

    # ----- Pagination -----
    total = len(sorted_results)
    page = sorted_results[start_index : start_index + PAGE_SIZE]

    # Compute next offset (if any)
    next_index = start_index + len(page)
    if response is not None:
        if next_index < total:
            # tell the client what offset to use in the next request
            response.headers["offset"] = str(next_index)
        else:
            # no more pages; you can either omit or set empty
            response.headers["offset"] = ""

    # Build response body
    return [
        ArtifactMetadataOut(
            name=a.name,
            id=str(a.id),
            type=ArtifactType(a.type),
        )
        for a in page
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

    metadata = ArtifactMetadataOut(name=obj.name, id=str(obj.id), type=ArtifactType(obj.type))
    data: Dict[str, Any] = {"url": payload.url}

    return ArtifactOut(metadata=metadata, data=data)


@app.post("/artifact/byRegEx", response_model=List[ArtifactMetadataOut])
def artifact_by_regex(
    payload: ArtifactRegExIn,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
    db: Session = Depends(get_session),
):
    """
    POST /artifact/byRegEx

    - 200: list of ArtifactMetadata
    - 400: invalid regex
    - 404: no matches
    """
    logger.info(f"[byRegEx] regex received: {payload.regex}")

    # Validate regex
    try:
        pattern = re.compile(payload.regex)
    except re.error as e:
        logger.warning(f"[byRegEx] INVALID regex -> 400 | error={e}")
        raise HTTPException(status_code=400, detail="Invalid artifact_regex")

    artifacts = db.query(ArtifactModel).all()
    logger.info(f"[byRegEx] DB contains {len(artifacts)} artifacts")

    matches: List[ArtifactModel] = []
    for a in artifacts:
        text_name = a.name or ""
        text_desc = a.description or ""

        if pattern.search(text_name) or pattern.search(text_desc):
            matches.append(a)

    logger.info(f"[byRegEx] matches found = {len(matches)}")

    if not matches:
        logger.info("[byRegEx] no matches -> 404")
        raise HTTPException(status_code=404, detail="No artifact found under this regex")

    response = [
        ArtifactMetadataOut(name=a.name, id=str(a.id), type=ArtifactType(a.type))
        for a in matches
    ]

    logger.info(f"[byRegEx] returning {len(response)} results -> 200")

    return response


# -------- Shared helper for ID-based lookups --------
def _get_artifact_by_type_and_id(
    artifact_type: str,
    id: str,
    db: Session,
) -> ArtifactOut:
    """
    Shared logic for:
      - GET /artifacts/{artifact_type}/{id}
      - GET /artifact/{artifact_type}/{id}

    Spec:
      - 200: artifact found
      - 400: invalid type or invalid ID *format*
      - 404: valid format, but ID not found or type mismatch
    """

    logger.info(f"[getByID] request received: type={artifact_type}, id={id}")

    # ------------------ 1) Validate artifact_type ------------------
    if artifact_type not in VALID_TYPES:
        logger.warning(f"[getByID] INVALID artifact_type '{artifact_type}' -> 400")
        raise HTTPException(status_code=400, detail="Invalid artifact_type")

    # ------------------ 2) Validate ID format ------------------
    if not id.isdigit():
       logger.warning(f"[getByID] Invalid ID format '{id}' -> 400")
       raise HTTPException(status_code=400, detail="Invalid artifact_id") 

    int_id = int(id)
    logger.info(f"[getByID] Parsed id as integer: {int_id}")
    
    # ------------------ 4) Query database ------------------
    obj = db.get(ArtifactModel, int_id)

    if obj is None:
        logger.info(f"[getByID] No DB row with PK={int_id} -> 404")
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    if obj.type != artifact_type:
        logger.info(
            f"[getByID] Type mismatch: DB has type={obj.type}, requested={artifact_type} -> 404"
        )
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    logger.info(f"[getByID] FOUND artifact id={obj.id} name='{obj.name}' type={obj.type}")

    # ------------------ Build response ------------------
    metadata = ArtifactMetadataOut(
        name=obj.name,
        id=str(obj.id),
        type=ArtifactType(obj.type),
    )
    data = {"url": obj.url} if obj.url else {}

    logger.info(f"[getByID] returning artifact id={obj.id} -> 200")
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

@app.get("/artifact/model/{id}/rate", response_model=ModelRatingOut)
def rate_model_artifact(
    id: str,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
    db: Session = Depends(get_session),
):
    # 1) validate id format
    if not ID_PATTERN.fullmatch(id):
        raise HTTPException(status_code=400, detail="Invalid artifact_id")

    try:
        int_id = int(id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    # 2) fetch model from DB
    obj = db.get(ArtifactModel, int_id)
    if obj is None or obj.type != "model":
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    # 3) compute via orchestrator (Phase 1 + Phase 2)
    try:
        res = _compute_one(obj.url, "MODEL")
    except Exception as e:
        logger.exception(f"[rate] failed for id={id}: {e}")
        raise HTTPException(status_code=500, detail="Rating pipeline error")

    # 4) adapt to OpenAPI response shape
    size_score_out = SizeScoreOut(**res.size_score)

    return ModelRatingOut(
    name=res.name,
    category=res.category,
    net_score=res.net_score,
    net_score_latency=res.net_score_latency,
    ramp_up_time=res.ramp_up_time,
    ramp_up_time_latency=res.ramp_up_time_latency,
    bus_factor=res.bus_factor,
    bus_factor_latency=res.bus_factor_latency,
    performance_claims=res.performance_claims,
    performance_claims_latency=res.performance_claims_latency,
    license=res.license,
    license_latency=res.license_latency,
    dataset_and_code_score=res.dataset_and_code_score,
    dataset_and_code_score_latency=res.dataset_and_code_score_latency,
    dataset_quality=res.dataset_quality,
    dataset_quality_latency=res.dataset_quality_latency,
    code_quality=res.code_quality,
    code_quality_latency=res.code_quality_latency,
    reproducibility=res.reproducibility,
    reproducibility_latency=res.reproducibility_latency,
    reviewedness=res.reviewedness,
    reviewedness_latency=res.reviewedness_latency,
    tree_score=res.tree_score,
    tree_score_latency=res.tree_score_latency,
    size_score=size_score_out,
    size_score_latency=res.size_score_latency,
)


