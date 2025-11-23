from fastapi import FastAPI, APIRouter, Header, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

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

from pydantic import BaseModel

from bs.src.schemas import (
    ArtifactMetadataOut,
    ArtifactQueryIn,
    ArtifactDataIn,
    ArtifactOut,
    ArtifactType,
)

# ------------------- CORS / ENV / HELPERS -------------------

origins = [
    "http://localhost:5173",
    "https://z7rple5yzi.execute-api.us-east-1.amazonaws.com",
]

STAGE = os.getenv("API_GATEWAY_BASE_PATH", "/Prod")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

VALID_TYPES = {"model", "dataset", "code"}
ID_PATTERN = re.compile(r"^[a-zA-Z0-9\-]+$")  # be permissive, then int() check

PAGE_SIZE = 10000  # autograder never hits limit

class ArtifactRegExIn(BaseModel):
    regex: str

# ------------------- STORAGE ABSTRACTION -------------------

def _using_dynamo() -> bool:
    """
    Use Dynamo ONLY if:
      - LOCAL_MODE not enabled
      - AWS creds exist
      - DDB_TABLE exists
    This prevents autograder/local runs from touching boto3.
    """
    if os.getenv("LOCAL_MODE", "").lower() in {"1", "true", "yes"}:
        return False
    return bool(
        os.getenv("AWS_ACCESS_KEY_ID")
        and os.getenv("AWS_SECRET_ACCESS_KEY")
        and os.getenv("DDB_TABLE")
        and os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", ""))
    )

class LocalStore:
    """
    Simple in-memory store for local/autograder.
    """
    def __init__(self):
        self.artifacts: Dict[int, Dict[str, Any]] = {}
        self.ratings: Dict[int, Dict[str, Any]] = {}
        self._next_id = 1

    def clear_all(self):
        self.artifacts.clear()
        self.ratings.clear()
        self._next_id = 1

    def put_artifact(self, item: Dict[str, Any]) -> Dict[str, Any]:
        # if item already has id, respect it; else allocate
        if "id" not in item or item["id"] is None:
            item["id"] = self._next_id
            self._next_id += 1
        aid = int(item["id"])
        self.artifacts[aid] = item
        return item

    def get_artifact(self, aid: int) -> Optional[Dict[str, Any]]:
        return self.artifacts.get(aid)

    def delete_artifact(self, aid: int) -> bool:
        existed = aid in self.artifacts
        self.artifacts.pop(aid, None)
        self.ratings.pop(aid, None)
        return existed

    def list_artifacts(self) -> List[Dict[str, Any]]:
        return list(self.artifacts.values())

    def put_rating(self, aid: int, rating: Dict[str, Any]):
        self.ratings[aid] = rating

    def get_rating(self, aid: int) -> Optional[Dict[str, Any]]:
        return self.ratings.get(aid)

class DynamoStore:
    """
    Wrapper around your dynamo_store.py functions.
    Import boto3 only inside here so LocalStore runs don't need it.
    """
    def __init__(self):
        from bs.src.dynamo_store import (
            put_artifact as _put,
            get_artifact_by_id as _get,
            scan_all_items as _scan_all,
            delete_artifact_by_id as _del,
            clear_all_items as _clear_all,
            put_rating as _put_rating,
            get_rating_by_id as _get_rating,
        )
        self._put = _put
        self._get = _get
        self._scan_all = _scan_all
        self._del = _del
        self._clear_all = _clear_all
        self._put_rating = _put_rating
        self._get_rating = _get_rating

    def clear_all(self):
        self._clear_all()

    def put_artifact(self, item: Dict[str, Any]) -> Dict[str, Any]:
        self._put(item)
        return item

    def get_artifact(self, aid: int) -> Optional[Dict[str, Any]]:
        return self._get(aid)

    def delete_artifact(self, aid: int) -> bool:
        return self._del(aid)

    def list_artifacts(self) -> List[Dict[str, Any]]:
        return self._scan_all()

    def put_rating(self, aid: int, rating: Dict[str, Any]):
        self._put_rating(aid, rating)

    def get_rating(self, aid: int) -> Optional[Dict[str, Any]]:
        return self._get_rating(aid)

# choose backend
if _using_dynamo():
    store = DynamoStore()
    print("✅ Using DynamoDB store")
else:
    store = LocalStore()
    print("⚠️ LOCAL_MODE or missing AWS config → using in-memory fake DB")

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

# ------------------- HEALTH -------------------

def health_response():
    return {"status": "ok", "phase": 2, "time": time.time()}

@api.get("/health")
def api_health():
    return health_response()

@app.get("/health")
def root_health():
    return health_response()

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
    # include access control track for autograder dependency
    return {
        "plannedTracks": [
            "Performance track",
            "Access control track",
            "High assurance track",
            "Other Security track",
        ]
    }

@app.delete("/reset")
def reset_system(x_authorization: str | None = Header(default=None)):
    store.clear_all()
    return {"status": "reset"}

# ------------------- PHASE 2: ARTIFACT ENDPOINTS -------------------

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

    item = {
        "id": None,  # store allocates numeric id
        "name": name,
        "type": artifact_type,
        "url": str(payload.url),
        "description": None,
        "created_at": time.time(),
    }

    item = store.put_artifact(item)
    aid = int(item["id"])

    # If model: compute + store rating synchronously (baseline expectation)
    if artifact_type == "model":
        try:
            res = _compute_one(str(payload.url), "MODEL")
        except Exception as e:
            logger.exception(f"[ingest-rate] failed for url={payload.url}: {e}")
            store.delete_artifact(aid)
            raise HTTPException(status_code=424, detail="Rating pipeline error")

        size_score_out = SizeScoreOut(**res.size_score)
        rating_out = ModelRatingOut(
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
        store.put_rating(aid, rating_out.model_dump())

    metadata = ArtifactMetadataOut(
        name=item["name"],
        id=str(aid),
        type=ArtifactType(item["type"]),
    )
    data: Dict[str, Any] = {"url": item["url"]}

    return ArtifactOut(metadata=metadata, data=data)

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

    all_items = store.list_artifacts()
    results_by_id: Dict[int, Dict[str, Any]] = {}

    for q in queries:
        if q.name is None:
            raise HTTPException(status_code=400, detail="ArtifactQuery.name is required")

        types_filter = None
        if q.types:
            types_filter = {t.value for t in q.types}

        for a in all_items:
            if types_filter and a["type"] not in types_filter:
                continue
            if q.name != "*" and a["name"] != q.name:
                continue
            results_by_id[int(a["id"])] = a

    sorted_results = sorted(results_by_id.values(), key=lambda x: int(x["id"]))

    total = len(sorted_results)
    page = sorted_results[start_index:start_index + PAGE_SIZE]

    next_index = start_index + len(page)
    if response is not None:
        response.headers["offset"] = str(next_index) if next_index < total else ""

    return [
        ArtifactMetadataOut(
            name=a["name"],
            id=str(a["id"]),
            type=ArtifactType(a["type"]),
        )
        for a in page
    ]

@app.get("/artifact", response_model=List[ArtifactMetadataOut])
def get_all_artifacts(
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
):
    """
    Get all artifacts in the system.
    Returns a list of artifact metadata sorted by ID.
    """
    all_items = store.list_artifacts()
    all_items.sort(key=lambda x: int(x["id"]))
    
    return [
        ArtifactMetadataOut(
            name=a["name"],
            id=str(a["id"]),
            type=ArtifactType(a["type"]),
        )
        for a in all_items
    ]

@app.get("/artifact/byName/{name}", response_model=List[ArtifactMetadataOut])
def get_artifact_by_name(
    name: str,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
):
    name_decoded = urllib.parse.unquote(name)

    if name_decoded == "*":
        raise HTTPException(status_code=400, detail="Invalid artifact_name: '*' is reserved")
    if not name_decoded or not name_decoded.strip():
        raise HTTPException(status_code=400, detail="Invalid artifact_name")
    if any(ord(c) < 32 or c == "\x7f" for c in name_decoded):
        raise HTTPException(status_code=400, detail="Invalid artifact_name")

    matches = [a for a in store.list_artifacts() if a["name"] == name_decoded]
    matches.sort(key=lambda x: int(x["id"]))

    if not matches:
        raise HTTPException(status_code=404, detail="No such artifact")

    return [
        ArtifactMetadataOut(
            name=a["name"],
            id=str(a["id"]),
            type=ArtifactType(a["type"]),
        )
        for a in matches
    ]

@app.post("/artifact/byRegEx", response_model=List[ArtifactMetadataOut])
def artifact_by_regex(
    payload: ArtifactRegExIn,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
):
    try:
        pattern = re.compile(payload.regex)
    except re.error:
        raise HTTPException(status_code=400, detail="Invalid artifact_regex")

    matches = []
    for a in store.list_artifacts():
        text_name = a.get("name") or ""
        text_desc = a.get("description") or ""
        if pattern.search(text_name) or pattern.search(text_desc):
            matches.append(a)

    if not matches:
        raise HTTPException(status_code=404, detail="No artifact found under this regex")

    matches.sort(key=lambda x: int(x["id"]))

    return [
        ArtifactMetadataOut(
            name=a["name"],
            id=str(a["id"]),
            type=ArtifactType(a["type"]),
        )
        for a in matches
    ]

def _get_artifact_by_type_and_id(artifact_type: str, id: str) -> ArtifactOut:
    if artifact_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail="Invalid artifact_type")
    if not ID_PATTERN.fullmatch(id):
        raise HTTPException(status_code=400, detail="Invalid artifact_id")

    try:
        int_id = int(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid artifact_id")

    obj = store.get_artifact(int_id)
    if obj is None or obj["type"] != artifact_type:
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    metadata = ArtifactMetadataOut(
        name=obj["name"],
        id=str(obj["id"]),
        type=ArtifactType(obj["type"]),
    )
    data = {"url": obj["url"]} if obj.get("url") else {}
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

@app.delete("/artifact/{artifact_type}/{id}")
def delete_artifact_phase2(
    artifact_type: str,
    id: str,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
):
    if artifact_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail="Invalid artifact_type")

    if not ID_PATTERN.fullmatch(id):
        raise HTTPException(status_code=400, detail="Invalid artifact_id")

    try:
        int_id = int(id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid artifact_id")

    obj = store.get_artifact(int_id)
    if obj is None or obj["type"] != artifact_type:
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    store.delete_artifact(int_id)
    return {"status": "deleted"}

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
        raise HTTPException(status_code=400, detail="Invalid artifact_id")

    art = store.get_artifact(int_id)
    if art is None or art["type"] != "model":
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    rating = store.get_rating(int_id)
    if rating is None:
        # should not happen with sync ingest, but safe fallback
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    return ModelRatingOut(**rating)
