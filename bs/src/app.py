
from fastapi import FastAPI, APIRouter, Header, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

# DynamoDB store (shared across Lambda instances)
from bs.src.dynamo_store import put_artifact, get_artifact_by_id, scan_all, reset_all

# acemcli rating pipeline (phase 1 + phase 2)
from bs.src.acemcli.orchestrator import _compute_one
# IMPORTANT: import metrics package to force registration side-effects
import bs.src.acemcli.metrics  # noqa: F401
from bs.src.schemas import ModelRatingOut, SizeScoreOut

import os
import time
import logging
import urllib.parse
import re
from typing import Dict, Any, Optional, List

# Phase 1 DB/router can stay for legacy /api/artifacts, but Phase 2 uses DynamoDB
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

import boto3
from boto3.dynamodb.conditions import Attr

# ------------------- CORS / ENV / HELPERS -------------------

origins = [
    "http://localhost:5173",
    "https://z7rple5yzi.execute-api.us-east-1.amazonaws.com",
]

STAGE = os.getenv("API_GATEWAY_BASE_PATH", "/Prod")

class ArtifactRegExIn(BaseModel):
    regex: str

VALID_TYPES = {"model", "dataset", "code"}
ID_PATTERN = re.compile(r"^[a-zA-Z0-9\-]+$")

# Dynamo table access (same table as dynamo_store.py)
DDB_TABLE = os.getenv("ARTIFACTS_TABLE", "ArtifactsTable")
_dynamo = boto3.resource("dynamodb")
_table = _dynamo.Table(DDB_TABLE)

def _scan_all_items() -> List[Dict[str, Any]]:
    """Scan entire Dynamo table and return items."""
    items: List[Dict[str, Any]] = []
    scan_kwargs = {}
    while True:
        resp = _table.scan(**scan_kwargs)
        items.extend(resp.get("Items", []))
        lek = resp.get("LastEvaluatedKey")
        if not lek:
            break
        scan_kwargs["ExclusiveStartKey"] = lek
    return items

def _delete_all_items() -> None:
    """Delete all artifacts from DynamoDB (used by /reset)."""
    items = _scan_all_items()
    if not items:
        return
    with _table.batch_writer() as batch:
        for it in items:
            # id is the partition key
            batch.delete_item(Key={"id": it["id"]})

# ------------------- FASTAPI APP SETUP -------------------

app = FastAPI(
    title="Team31 Backend (Phase 2)",
    docs_url=None,
    redoc_url=None,
    openapi_url="/openapi.json",
    root_path=STAGE,
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
    start = time.time()

    path = request.url.path
    method = request.method
    query = str(request.url.query)

    auth_header = request.headers.get("X-Authorization")
    has_auth = auth_header is not None

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
    logger.info(f"RESP {method} {path} -> {response.status_code} ({duration_ms:.1f}ms)")

    return response

api = APIRouter(prefix="/api")

# ------------------- Health & Legacy router -------------------

def health_response():
    return {"status": "ok", "phase": 2, "time": time.time()}

@api.get("/health")
def api_health():
    return health_response()

@app.get("/health")
def root_health():
    return health_response()

# Legacy Phase 1 CRUD router for /api/artifacts (not used by autograder Phase 2 baseline)
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
    return {"plannedTracks": []}

@app.delete("/reset")
def reset_system(x_authorization: str | None = Header(default=None)):
    """
    Reset the registry to an empty state.
    Works in LOCAL_MODE (in-memory) and AWS mode (DynamoDB).
    """
    reset_all()
    return {"status": "reset"}

# ------------------- PHASE 2: ARTIFACT ENDPOINTS -------------------

PAGE_SIZE = 10000  # large enough so autograder never hits the limit

@app.post("/artifacts", response_model=List[ArtifactMetadataOut])
def list_artifacts_phase2(
    queries: List[ArtifactQueryIn],
    offset: Optional[str] = None,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
    response: Response = None,
):
    if not queries:
        raise HTTPException(status_code=400, detail="At least one query is required")

    try:
        start_index = int(offset) if offset is not None else 0
        if start_index < 0:
            raise ValueError()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid offset")

    # Build dynamo scans per query
    results_by_id: Dict[int, Dict[str, Any]] = {}

    for q in queries:
        if q.name is None:
            raise HTTPException(status_code=400, detail="ArtifactQuery.name is required")

        fe = None
        # name filter except wildcard
        if q.name != "*":
            fe = Attr("name").eq(q.name)

        # types filter
        if q.types:
            type_vals = [t.value for t in q.types]
            tfe = Attr("type").is_in(type_vals)
            fe = tfe if fe is None else fe & tfe

        if fe is not None:
            resp = _table.scan(FilterExpression=fe)
        else:
            resp = _table.scan()

        for item in resp.get("Items", []):
            # id in dynamo is Number -> int/Decimal; normalize to int for sorting
            try:
                iid = int(item["id"])
            except Exception:
                continue
            results_by_id[iid] = item

    sorted_items = [results_by_id[k] for k in sorted(results_by_id.keys())]

    total = len(sorted_items)
    page = sorted_items[start_index : start_index + PAGE_SIZE]

    next_index = start_index + len(page)
    if response is not None:
        response.headers["offset"] = str(next_index) if next_index < total else ""

    return [
        ArtifactMetadataOut(
            name=item["name"],
            id=str(item["id"]),
            type=ArtifactType(item["type"]),
        )
        for item in page
    ]

@app.post("/artifact/{artifact_type}", response_model=ArtifactOut, status_code=201)
def ingest_artifact_phase2(
    artifact_type: str,
    payload: ArtifactDataIn,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
):
    if artifact_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail="Invalid artifact_type")

    parsed = urllib.parse.urlparse(str(payload.url))
    name = parsed.path.rstrip("/").split("/")[-1] or "artifact"

    # Generate stable numeric id
    aid = int(time.time() * 1000) % 10_000_000

    item = {
        "id": aid,
        "name": name,
        "type": artifact_type,
        "url": str(payload.url),
        "description": None,
        "created_at": time.time(),
    }
    put_artifact(item)

    metadata = ArtifactMetadataOut(name=name, id=str(aid), type=ArtifactType(artifact_type))
    data: Dict[str, Any] = {"url": payload.url}

    return ArtifactOut(metadata=metadata, data=data)

@app.post("/artifact/byRegEx", response_model=List[ArtifactMetadataOut])
def artifact_by_regex(
    payload: ArtifactRegExIn,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
):
    logger.info(f"[byRegEx] regex received: {payload.regex}")

    try:
        pattern = re.compile(payload.regex)
    except re.error as e:
        logger.warning(f"[byRegEx] INVALID regex -> 400 | error={e}")
        raise HTTPException(status_code=400, detail="Invalid artifact_regex")

    items = _scan_all_items()
    matches: List[Dict[str, Any]] = []

    for it in items:
        text_name = (it.get("name") or "")
        text_desc = (it.get("description") or "")
        if pattern.search(text_name) or pattern.search(text_desc):
            matches.append(it)

    if not matches:
        raise HTTPException(status_code=404, detail="No artifact found under this regex")

    # sort by id ASC
    matches.sort(key=lambda x: int(x.get("id", 0)))

    return [
        ArtifactMetadataOut(
            name=it["name"],
            id=str(it["id"]),
            type=ArtifactType(it["type"]),
        )
        for it in matches
    ]

@app.get("/artifact/byName/{name}", response_model=List[ArtifactMetadataOut])
def get_artifact_by_name(
    name: str,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
):
    logger.info(f"[byName] raw name received: {name}")
    name_decoded = urllib.parse.unquote(name)
    logger.info(f"[byName] decoded name: {name_decoded}")

    if name_decoded == "*":
        raise HTTPException(status_code=400, detail="Invalid artifact_name: '*' is reserved")

    if not name_decoded or not name_decoded.strip():
        raise HTTPException(status_code=400, detail="Invalid artifact_name")

    if any(ord(c) < 32 or c == "\x7f" for c in name_decoded):
        raise HTTPException(status_code=400, detail="Invalid artifact_name")

    resp = _table.scan(FilterExpression=Attr("name").eq(name_decoded))
    items = resp.get("Items", [])
    if not items:
        raise HTTPException(status_code=404, detail="No such artifact")

    items.sort(key=lambda x: int(x.get("id", 0)))

    return [
        ArtifactMetadataOut(
            name=it["name"],
            id=str(it["id"]),
            type=ArtifactType(it["type"]),
        )
        for it in items
    ]

# -------- Shared helper for ID-based lookups (DynamoDB) --------
def _get_artifact_by_type_and_id(
    artifact_type: str,
    id: str,
) -> ArtifactOut:
    logger.info(f"[getByID] request received: type={artifact_type}, id={id}")

    if artifact_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail="Invalid artifact_type")

    if not ID_PATTERN.fullmatch(id):
        raise HTTPException(status_code=400, detail="Invalid artifact_id")

    try:
        int_id = int(id)
    except ValueError:
        # valid format but not numeric -> treat as not found
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    obj = get_artifact_by_id(int_id)
    if obj is None or obj.get("type") != artifact_type:
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    metadata = ArtifactMetadataOut(
        name=obj["name"],
        id=str(obj["id"]),
        type=ArtifactType(obj["type"]),
    )
    data: Dict[str, Any] = {"url": obj.get("url")} if obj.get("url") else {}

    return ArtifactOut(metadata=metadata, data=data)

@app.get("/artifacts/{artifact_type}/{id}", response_model=ArtifactOut)
def get_artifact_phase2(
    artifact_type: str,
    id: str,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
):
    return _get_artifact_by_type_and_id(artifact_type, id)

@app.get("/artifact/{artifact_type}/{id}", response_model=ArtifactOut)
def get_artifact_phase2_singular(
    artifact_type: str,
    id: str,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
):
    return _get_artifact_by_type_and_id(artifact_type, id)

@app.get("/artifact/model/{id}/rate", response_model=ModelRatingOut)
def rate_model_artifact(
    id: str,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
):
    if not ID_PATTERN.fullmatch(id):
        raise HTTPException(status_code=400, detail="Invalid artifact_id")

    try:
        int_id = int(id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    obj = get_artifact_by_id(int_id)
    if obj is None or obj.get("type") != "model":
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    url = obj.get("url")
    if not url:
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    try:
        res = _compute_one(url, "MODEL")
    except Exception as e:
        logger.exception(f"[rate] failed for id={id}: {e}")
        raise HTTPException(status_code=500, detail="Rating pipeline error")

    # robust size score handling
    size_raw = res.size_score
    if hasattr(size_raw, "model_dump"):
        size_raw = size_raw.model_dump()
    elif not isinstance(size_raw, dict):
        size_raw = dict(size_raw)

    size_score_out = SizeScoreOut(**size_raw)

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

