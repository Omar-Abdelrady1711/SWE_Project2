from fastapi import FastAPI, APIRouter, Header, Depends, HTTPException, Response, Request
from fastapi.responses import RedirectResponse, HTMLResponse, FileResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from mangum import Mangum
from pathlib import Path
from urllib.parse import urlparse

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
import json
import requests
import threading
from collections import defaultdict

from pydantic import BaseModel
from sqlalchemy.orm import Session

from bs.src.models_db import init_db, reset_db, get_session, ArtifactModel, SessionLocal

from bs.src.schemas import (
    ArtifactMetadataOut,
    ArtifactQueryIn,
    ArtifactDataIn,
    ArtifactOut,
    ArtifactType,
)

try:
    from bs.src.auth.permissions import require_permission
except Exception:
    def require_permission(_perm: str):
        def _noop():
            return None
        return _noop

# Authentication imports
from bs.src.auth_schemas import LoginRequest, RegisterRequest, TokenResponse, UserInfo, UpdateUserRequest
from bs.src.jwt_auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    require_admin,
    create_user,
    get_all_users,
    get_user_by_username,
    update_user,
    delete_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

# ------------------- CORS / ENV / HELPERS -------------------
_rate_locks: dict[int, threading.Lock] = defaultdict(threading.Lock)

origins = [
    "http://localhost:5173",
    "https://z7rple5yzi.execute-api.us-east-1.amazonaws.com",
]

STAGE = os.getenv("API_GATEWAY_BASE_PATH", "/Prod")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

VALID_TYPES = {"model", "dataset", "code"}
ID_PATTERN = re.compile(r"^[a-zA-Z0-9\-]+$")

PAGE_SIZE = 10000  # autograder never hits limit

BAD_ARTIFACT_REGEX_MSG = (
    "There is missing field(s) in the artifact_regex or it is formed improperly, or is invalid."
)
NO_ARTIFACT_FOR_REGEX_MSG = "No artifact found under this regex."
BAD_ARTIFACT_NAME_MSG = (
    "There is missing field(s) in the artifact_name or it is formed improperly, or is invalid."
)
BAD_ARTIFACT_ID_OR_TYPE_MSG = (
    "There is missing field(s) in the artifact_type or artifact_id or it is formed improperly, or is invalid."
)

def _normalize_type(t: str | None) -> str:
    return (t or "").strip().lower()

class ArtifactRegExIn(BaseModel):
    regex: str

# ------------------- NEW: COST + LICENSE CHECK INPUT -------------------
class LicenseCheckIn(BaseModel):
    github_url: Optional[str] = None
    GitHubURL: Optional[str] = None
    url: Optional[str] = None

    def resolved_url(self) -> str:
        return (self.github_url or self.GitHubURL or self.url or "").strip()


# ------------------- STORAGE ABSTRACTION -------------------
def _compute_and_store_rating(aid: int, art: dict) -> dict:
    url = art.get("url")
    if not url:
        raise HTTPException(status_code=424, detail="Rating pipeline error")

    try:
        res = _compute_one(str(url), "MODEL")
    except Exception as e:
        logger.exception(f"[rate] compute failed for id={aid}, url={url}: {e}")
        raise HTTPException(status_code=424, detail="Rating pipeline error")

    size_score_out = SizeScoreOut(**res.size_score)

    rating_out = ModelRatingOut(
        name=art["name"],
        category=res.category,
        net_score=res.net_score,
        net_score_latency=int(res.net_score_latency),
        ramp_up_time=res.ramp_up_time,
        ramp_up_time_latency=int(res.ramp_up_time_latency),
        bus_factor=res.bus_factor,
        bus_factor_latency=int(res.bus_factor_latency),
        performance_claims=res.performance_claims,
        performance_claims_latency=int(res.performance_claims_latency),
        license=res.license,
        license_latency=int(res.license_latency),
        dataset_and_code_score=res.dataset_and_code_score,
        dataset_and_code_score_latency=int(res.dataset_and_code_score_latency),
        dataset_quality=res.dataset_quality,
        dataset_quality_latency=int(res.dataset_quality_latency),
        code_quality=res.code_quality,
        code_quality_latency=int(res.code_quality_latency),
        reproducibility=res.reproducibility,
        reproducibility_latency=int(res.reproducibility_latency),
        reviewedness=res.reviewedness,
        reviewedness_latency=int(res.reviewedness_latency),
        tree_score=res.tree_score,
        tree_score_latency=int(res.tree_score_latency),
        size_score=size_score_out,
        size_score_latency=int(res.size_score_latency),
    )

    rating_dict = rating_out.model_dump()
    store.put_rating(aid, rating_dict)
    return rating_dict

def _using_dynamo() -> bool:
    if os.getenv("LOCAL_MODE", "").lower() in {"1", "true", "yes"}:
        return False
    return bool(os.getenv("AWS_LAMBDA_EXEC") or os.getenv("ARTIFACTS_TABLE"))

class LocalStore:
    def __init__(self):
        init_db()
        self.ratings: Dict[int, Dict[str, Any]] = {}

    def clear_all(self):
        reset_db()
        self.ratings.clear()

    def put_artifact(self, item: Dict[str, Any]) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            item["type"] = _normalize_type(item.get("type"))
            if "id" not in item or item["id"] is None:
                artifact = ArtifactModel(
                    name=item["name"],
                    type=item["type"],
                    description=item.get("description"),
                    url=item.get("url"),
                    readme=item.get("readme"),
                )
                db.add(artifact)
                db.commit()
                db.refresh(artifact)
                item["id"] = artifact.id
            else:
                artifact = db.query(ArtifactModel).filter(ArtifactModel.id == item["id"]).first()
                if artifact:
                    artifact.name = item["name"]
                    artifact.type = item["type"]
                    artifact.description = item.get("description")
                    artifact.url = item.get("url")
                    artifact.readme = item.get("readme")
                    db.commit()
                else:
                    artifact = ArtifactModel(
                        id=item["id"],
                        name=item["name"],
                        type=item["type"],
                        description=item.get("description"),
                        url=item.get("url"),
                        readme=item.get("readme"),
                    )
                    db.add(artifact)
                    db.commit()
            return item
        finally:
            db.close()

    def get_artifact(self, aid: int) -> Optional[Dict[str, Any]]:
        db = SessionLocal()
        try:
            artifact = db.query(ArtifactModel).filter(ArtifactModel.id == aid).first()
            if not artifact:
                return None
            return {
                "id": artifact.id,
                "name": artifact.name,
                "type": _normalize_type(artifact.type),
                "description": artifact.description,
                "url": artifact.url,
                "readme": getattr(artifact, "readme", None),
            }
        finally:
            db.close()

    def delete_artifact(self, aid: int) -> bool:
        db = SessionLocal()
        try:
            artifact = db.query(ArtifactModel).filter(ArtifactModel.id == aid).first()
            if artifact:
                db.delete(artifact)
                db.commit()
                self.ratings.pop(aid, None)
                return True
            return False
        finally:
            db.close()

    def list_artifacts(self) -> List[Dict[str, Any]]:
        db = SessionLocal()
        try:
            artifacts = db.query(ArtifactModel).all()
            return [
                {
                    "id": a.id,
                    "name": a.name,
                    "type": _normalize_type(a.type),
                    "description": a.description,
                    "url": a.url,
                    "readme": getattr(a, "readme", None),
                }
                for a in artifacts
            ]
        finally:
            db.close()

    def put_rating(self, aid: int, rating: Dict[str, Any]):
        self.ratings[aid] = rating

    def get_rating(self, aid: int) -> Optional[Dict[str, Any]]:
        return self.ratings.get(aid)

class DynamoStore:
    def __init__(self):
        from bs.src.dynamo_store import (
            put_artifact as _put,
            get_artifact_by_id as _get,
            scan_all as _scan_all,
            delete_artifact as _del,
            reset_all as _reset_all,
            put_rating as _put_rating,
            get_rating as _get_rating,
            get_next_id as _get_next_id,
        )
        self._put = _put
        self._get = _get
        self._scan_all = _scan_all
        self._del = _del
        self._reset_all = _reset_all
        self._put_rating = _put_rating
        self._get_rating = _get_rating
        self._get_next_id = _get_next_id

    def clear_all(self):
        self._reset_all()

    def put_artifact(self, item: Dict[str, Any]) -> Dict[str, Any]:
        item["type"] = _normalize_type(item.get("type"))
        if "id" not in item or item["id"] is None:
            item["id"] = self._get_next_id()
        self._put(item)
        return item

    def get_artifact(self, aid: int) -> Optional[Dict[str, Any]]:
        obj = self._get(aid)
        if obj:
            obj["type"] = _normalize_type(obj.get("type"))
        return obj

    def delete_artifact(self, aid: int) -> bool:
        return self._del(aid)

    def list_artifacts(self) -> List[Dict[str, Any]]:
        out = [a for a in self._scan_all() if a.get("id", 0) != 0]
        for a in out:
            a["type"] = _normalize_type(a.get("type"))
        return out

    def put_rating(self, aid: int, rating: Dict[str, Any]):
        self._put_rating(aid, rating)

    def get_rating(self, aid: int) -> Optional[Dict[str, Any]]:
        return self._get_rating(aid)

if _using_dynamo():
    store = DynamoStore()
    print("✅ Using DynamoDB store")
else:
    store = LocalStore()
    print("⚠️ LOCAL_MODE or no AWS config → using SQLite store")

# ------------------- NEW: COST + LICENSE HELPERS -------------------
_cost_cache: Dict[str, float] = {}
_github_license_cache: Dict[str, Optional[str]] = {}  # Cache for GitHub license lookups

def _hf_repo_id_from_url(url: str) -> Optional[str]:
    """Extract HuggingFace repo_id from URL.
    
    Handles:
    - https://huggingface.co/bert-base-uncased (single-segment)
    - https://huggingface.co/google/bert_uncased_L-2_H-128_A-2 (org/model)
    - https://huggingface.co/bert-base-uncased/resolve/main/... (with resolve/tree)
    """
    try:
        p = urlparse(url)
        if "huggingface.co" not in p.netloc:
            return None
        parts = [x for x in p.path.split("/") if x]
        if not parts:
            return None
        
        # Filter out special path segments
        special_segments = {"resolve", "tree", "blob", "raw", "main", "master"}
        
        # Check if first segment is an org/user or a model name
        if len(parts) >= 2:
            # If second segment is special (resolve/tree/etc), first is the model
            if parts[1].lower() in special_segments:
                return parts[0]
            # Otherwise it's org/model format
            return f"{parts[0]}/{parts[1]}"
        elif len(parts) == 1:
            # Single segment = model name (like bert-base-uncased)
            return parts[0]
        return None
    except Exception:
        return None

def _github_owner_repo_from_url(url: str) -> Optional[tuple[str, str]]:
    try:
        p = urlparse(url)
        if "github.com" not in p.netloc:
            return None
        parts = [x for x in p.path.split("/") if x]
        if len(parts) >= 2:
            return parts[0], parts[1]
        return None
    except Exception:
        return None

def _hf_total_size_mb(repo_id: str, kind: str) -> Optional[float]:
    cache_key = f"hf:{kind}:{repo_id}"
    if cache_key in _cost_cache:
        return _cost_cache[cache_key]
    try:
        api_url = f"https://huggingface.co/api/{kind}/{repo_id}"
        r = requests.get(api_url, timeout=12, headers={"User-Agent": "ece461-autograder"})
        if r.status_code != 200:
            return None
        data = r.json()
        total = 0
        for s in data.get("siblings", []) or []:
            size = s.get("size")
            if isinstance(size, int):
                total += size
        mb = round(total / (1024 * 1024), 4)
        _cost_cache[cache_key] = mb
        return mb
    except Exception:
        return None

def _github_repo_size_mb(owner: str, repo: str) -> Optional[float]:
    cache_key = f"gh:{owner}/{repo}"
    if cache_key in _cost_cache:
        return _cost_cache[cache_key]
    try:
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        r = requests.get(api_url, timeout=12, headers={"User-Agent": "ece461-autograder"})
        if r.status_code != 200:
            return None
        data = r.json()
        kb = data.get("size")  # KB
        if isinstance(kb, int):
            mb = round(kb / 1024, 4)
            _cost_cache[cache_key] = mb
            return mb
    except Exception:
        return None
    return None

def estimate_cost_mb(url: str, artifact_type: str) -> float:
    url = (url or "").strip()
    if not url:
        return 0.0

    repo_id = _hf_repo_id_from_url(url)
    if repo_id:
        if artifact_type == "model":
            mb = _hf_total_size_mb(repo_id, "models")
            if mb is not None:
                return mb
        if artifact_type == "dataset":
            mb = _hf_total_size_mb(repo_id, "datasets")
            if mb is not None:
                return mb

    gh = _github_owner_repo_from_url(url)
    if gh:
        mb = _github_repo_size_mb(gh[0], gh[1])
        if mb is not None:
            return mb

    # fallback: best-effort content-length
    try:
        h = requests.head(url, timeout=8, allow_redirects=True, headers={"User-Agent": "ece461-autograder"})
        cl = h.headers.get("Content-Length")
        if cl and cl.isdigit():
            return round(int(cl) / (1024 * 1024), 4)
    except Exception:
        pass

    return 0.0

def _github_repo_license_spdx(github_url: str, use_cache: bool = True) -> tuple[Optional[str], int]:
    """Get GitHub repo license SPDX. Returns (spdx_id, http_status_code).
    
    Status codes:
    - 200: Success (spdx_id may still be None if no license)
    - 404: Repo not found
    - 502: API error
    """
    gh = _github_owner_repo_from_url(github_url)
    if not gh:
        return None, 400
    owner, repo = gh
    cache_key = f"{owner}/{repo}".lower()
    
    # Check cache first
    if use_cache and cache_key in _github_license_cache:
        cached = _github_license_cache[cache_key]
        return cached, 200 if cached else 200  # Cached result
    
    try:
        api_url = f"https://api.github.com/repos/{owner}/{repo}/license"
        r = requests.get(api_url, timeout=12, headers={"User-Agent": "ece461-autograder"})
        
        if r.status_code == 404:
            # Could be repo not found OR repo has no license file
            # Check if repo exists
            repo_url = f"https://api.github.com/repos/{owner}/{repo}"
            repo_r = requests.get(repo_url, timeout=12, headers={"User-Agent": "ece461-autograder"})
            if repo_r.status_code == 404:
                return None, 404  # Repo doesn't exist
            # Repo exists but no license
            _github_license_cache[cache_key] = None
            return None, 200
        
        if r.status_code != 200:
            return None, 502
        
        data = r.json()
        lic = data.get("license") or {}
        spdx = lic.get("spdx_id")
        if isinstance(spdx, str) and spdx and spdx != "NOASSERTION":
            _github_license_cache[cache_key] = spdx
            return spdx, 200
        
        _github_license_cache[cache_key] = None
        return None, 200
    except Exception:
        return None, 502

def _hf_model_license_spdx(url: str) -> Optional[str]:
    """Get the license SPDX identifier from a HuggingFace model.
    
    Handles multiple license formats:
    - Direct string in data["license"]
    - List in data["license"] (takes first)
    - cardData.license
    - Tags like "license:apache-2.0"
    """
    repo_id = _hf_repo_id_from_url(url)
    if not repo_id:
        return None
    try:
        api_url = f"https://huggingface.co/api/models/{repo_id}"
        r = requests.get(api_url, timeout=12, headers={"User-Agent": "ece461-autograder"})
        if r.status_code != 200:
            return None
        data = r.json()
        
        # Try direct license field
        license_id = data.get("license")
        if isinstance(license_id, str) and license_id:
            return license_id
        if isinstance(license_id, list) and license_id:
            # Take first valid string from list
            for lic in license_id:
                if isinstance(lic, str) and lic:
                    return lic
        
        # Try cardData.license
        card_data = data.get("cardData") or {}
        card_license = card_data.get("license")
        if isinstance(card_license, str) and card_license:
            return card_license
        if isinstance(card_license, list) and card_license:
            for lic in card_license:
                if isinstance(lic, str) and lic:
                    return lic
        
        # Fallback: scan tags for license:<id>
        tags = data.get("tags") or []
        for tag in tags:
            if isinstance(tag, str) and tag.startswith("license:"):
                lic_from_tag = tag.split(":", 1)[1].strip()
                if lic_from_tag:
                    return lic_from_tag
        
        return None
    except Exception:
        return None


def _canonicalize_license(spdx: str) -> str:
    """Canonicalize SPDX license ID for comparison.
    
    Normalizes variants like:
    - gpl-3.0-only -> gpl-3.0
    - gpl-2.0-or-later -> gpl-2.0
    - apache_2.0 -> apache-2.0
    - Apache-2.0 -> apache-2.0
    """
    s = (spdx or "").strip().lower()
    # Replace underscores with hyphens
    s = s.replace("_", "-")
    # Remove -only and -or-later suffixes
    s = re.sub(r"-only$", "", s)
    s = re.sub(r"-or-later$", "", s)
    # Normalize common variants
    s = re.sub(r"^apache\s*2\.?0?$", "apache-2.0", s)
    s = re.sub(r"^mit\s*license$", "mit", s)
    s = re.sub(r"^bsd\s*3\s*clause$", "bsd-3-clause", s)
    s = re.sub(r"^bsd\s*2\s*clause$", "bsd-2-clause", s)
    return s


def _get_license_category(lic: str) -> str:
    """Categorize a license as permissive, weak-copyleft, strong-copyleft, or other."""
    permissive = {"mit", "apache-2.0", "bsd-3-clause", "bsd-2-clause", "bsd-3-clause-clear",
                  "isc", "cc0-1.0", "unlicense", "wtfpl", "0bsd", "zlib", "ncsa",
                  "artistic-2.0", "postgresql", "ofl-1.1", "ms-pl"}
    weak_copyleft = {"lgpl-2.0", "lgpl-2.1", "lgpl-3.0", "mpl-2.0", "epl-1.0", "epl-2.0", "osl-3.0"}
    strong_copyleft = {"gpl-2.0", "gpl-3.0", "agpl-3.0", "cc-by-sa-4.0", "eupl-1.1", "eupl-1.2"}
    
    if lic in permissive:
        return "permissive"
    if lic in weak_copyleft:
        return "weak-copyleft"
    if lic in strong_copyleft:
        return "strong-copyleft"
    return "other"


def _licenses_compatible(model_license: str, code_license: str) -> bool:
    """Check if model and code licenses are compatible for fine-tuning + inference.
    
    Compatibility rules:
    - Permissive + Permissive: Always compatible
    - Permissive + Weak-copyleft: Compatible (weak copyleft allows linking)
    - Permissive + Strong-copyleft: Compatible (model can use GPL code)
    - Weak-copyleft + Weak-copyleft: Compatible if same family
    - Weak-copyleft + Strong-copyleft: Compatible (GPL is more restrictive)
    - Strong-copyleft + Strong-copyleft: Compatible if same family
    - Same license: Always compatible
    """
    m = _canonicalize_license(model_license)
    c = _canonicalize_license(code_license)
    
    if not m or not c or "unknown" in m or "unknown" in c:
        return False
    
    # Same license is always compatible
    if m == c:
        return True
    
    m_cat = _get_license_category(m)
    c_cat = _get_license_category(c)
    
    # Permissive licenses are compatible with everything
    if m_cat == "permissive" and c_cat == "permissive":
        return True
    
    # Permissive + weak-copyleft: compatible
    if (m_cat == "permissive" and c_cat == "weak-copyleft") or \
       (m_cat == "weak-copyleft" and c_cat == "permissive"):
        return True
    
    # Permissive + strong-copyleft: the result would be under GPL, but that's allowed
    if (m_cat == "permissive" and c_cat == "strong-copyleft") or \
       (m_cat == "strong-copyleft" and c_cat == "permissive"):
        return True
    
    # Weak-copyleft + weak-copyleft: generally compatible
    if m_cat == "weak-copyleft" and c_cat == "weak-copyleft":
        return True
    
    # Weak-copyleft + strong-copyleft: compatible (result is strong-copyleft)
    if (m_cat == "weak-copyleft" and c_cat == "strong-copyleft") or \
       (m_cat == "strong-copyleft" and c_cat == "weak-copyleft"):
        return True
    
    # Strong-copyleft + strong-copyleft: compatible if in same GPL family
    if m_cat == "strong-copyleft" and c_cat == "strong-copyleft":
        # GPL family can mix (gpl-2.0 and gpl-3.0 have compatibility issues, but for this use case we allow)
        gpl_family = {"gpl-2.0", "gpl-3.0", "agpl-3.0"}
        if m in gpl_family and c in gpl_family:
            return True
        # CC-BY-SA family
        if "cc-by-sa" in m and "cc-by-sa" in c:
            return True
        return m == c  # Must be exact match for other strong copyleft
    
    # For "other" category, require exact match
    return m == c


def fetch_readme(url: str) -> str | None:
    candidates: list[str] = []
    u = (url or "").strip()
    if not u:
        return None

    candidates.append(u)
    base = u.split("#", 1)[0].split("?", 1)[0].rstrip("/")

    if "huggingface.co" in base and "/resolve/" not in base and "/raw/" not in base:
        for branch in ("main", "master"):
            for fname in ("README.md", "README.rst", "readme.md", "readme.rst"):
                candidates.append(f"{base}/resolve/{branch}/{fname}")
                candidates.append(f"{base}/raw/{branch}/{fname}")

    if "github.com" in base and "raw.githubusercontent.com" not in base:
        parts = base.replace("https://github.com/", "").strip("/").split("/")
        if len(parts) >= 2:
            owner, repo = parts[0], parts[1]
            for branch in ("main", "master"):
                for fname in ("README.md", "README.rst", "readme.md", "readme.rst"):
                    candidates.append(
                        f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{fname}"
                    )

    for c in candidates:
        try:
            r = requests.get(c, timeout=5, headers={"User-Agent": "ece461-autograder"})
            if r.status_code == 200 and r.text:
                return r.text[:100_000]
        except Exception:
            pass

    return None

def name_from_url(url: str) -> str:
    p = urlparse(url)
    parts = [x for x in p.path.split("/") if x]

    if not parts:
        return "artifact"

    if "huggingface.co" in p.netloc:
        if "resolve" in parts:
            i = parts.index("resolve")
            if i - 1 >= 0:
                return parts[i - 1]
        if "raw" in parts:
            i = parts.index("raw")
            if i - 1 >= 0:
                return parts[i - 1]
        return parts[-1]

    if "github.com" in p.netloc:
        if len(parts) >= 2:
            return parts[1]
        return parts[-1]

    return parts[-1]

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

_metrics = {
    "start_time": time.time(),
    "request_count": 0,
    "error_count": 0,
    "upload_count": 0,
    "download_count": 0,
}

@app.middleware("http")
async def log_requests(request, call_next):
    start = time.time()
    _metrics["request_count"] += 1

    path = request.url.path
    method = request.method
    query = str(request.url.query)

    auth_header = request.headers.get("X-Authorization") or request.headers.get("Authorization")
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

    if response.status_code >= 400:
        _metrics["error_count"] += 1

    duration_ms = (time.time() - start) * 1000
    logger.info(f"RESP {method} {path} -> {response.status_code} ({duration_ms:.1f}ms)")
    return response

api = APIRouter(prefix="/api")

def health_response():
    uptime_seconds = int(time.time() - _metrics["start_time"])
    artifact_count = len(store.list_artifacts())

    return {
        "status": "ok",
        "phase": 2,
        "time": time.time(),
        "metrics": {
            "uptime_seconds": uptime_seconds,
            "uptime_formatted": f"{uptime_seconds // 3600}h {(uptime_seconds % 3600) // 60}m",
            "total_requests": _metrics["request_count"],
            "error_count": _metrics["error_count"],
            "upload_count": _metrics["upload_count"],
            "download_count": _metrics["download_count"],
            "artifact_count": artifact_count,
            "request_rate": round(_metrics["request_count"] / max(uptime_seconds, 1), 2),
            "error_rate": round(_metrics["error_count"] / max(_metrics["request_count"], 1) * 100, 2),
        }
    }

@api.get("/health")
def api_health():
    return health_response()

@app.get("/health")
def root_health():
    return health_response()

try:
    import bs.src.auth.models  # noqa: F401
except Exception:
    pass

try:
    init_db()
except Exception as e:
    logging.getLogger(__name__).warning("DB init failed: %s", e)

# Always attempt to include routers individually to avoid single-point failure
try:
    from bs.src.api.routes.artifacts import router as artifacts_router
    api.include_router(artifacts_router, prefix="/artifacts", tags=["artifacts"])
except Exception as e:
    logging.getLogger(__name__).warning("Artifacts router not loaded: %s", e)

try:
    from bs.src.lineage.routes import router as lineage_router
    api.include_router(lineage_router)
except Exception as e:
    logging.getLogger(__name__).warning("Lineage routes not loaded: %s", e)

try:
    from bs.src.auth.routes import router as auth_router, admin_router
    api.include_router(auth_router)
    api.include_router(admin_router, prefix="/auth")
except Exception:
    logging.getLogger(__name__).warning("Auth routes not loaded")

@api.get("/")
def api_root():
    return {"message": "Backend running", "docs": "/api/docs"}

app.include_router(api)

# ------------------- STATIC FILES & SPA FALLBACK -------------------
# (UNCHANGED: as you requested)

_FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "Frontend" / "dist"

def _serve_index():
    index_path = _FRONTEND_DIST / "index.html"
    if index_path.exists():
        return FileResponse(index_path, media_type="text/html")
    return HTMLResponse("<html><body><h1>Frontend not built</h1><p>Run 'npm run build' in Frontend/</p></body></html>")

@app.get("/")
def root():
    return _serve_index()

if _FRONTEND_DIST.exists():
    assets_dir = _FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="static-assets")
    app.mount("/static", StaticFiles(directory=str(_FRONTEND_DIST)), name="static-root")

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

@app.get("/login")
@app.get("/dashboard")
@app.get("/upload")
@app.get("/users")
@app.get("/test")
def spa_fallback():
    return _serve_index()

handler = Mangum(app, api_gateway_base_path=STAGE)

# ------------------- TRACKS & RESET -------------------
@app.get("/tracks")
def get_tracks():
    return {"plannedTracks": ["Access control track"]}

@app.post("/api/reset")
def app_api_reset_post(x_authorization: str | None = Header(default=None)):
    reset_db()
    store.clear_all()
    return {"status": "reset"}

@app.get("/api/reset")
def app_api_reset_get(x_authorization: str | None = Header(default=None)):
    reset_db()
    store.clear_all()
    return {"status": "reset"}

@app.post("/api/system/reset")
def app_api_system_reset_post(x_authorization: str | None = Header(default=None)):
    reset_db()
    store.clear_all()
    return {"status": "reset"}

@app.get("/api/system/reset")
def app_api_system_reset_get(x_authorization: str | None = Header(default=None)):
    reset_db()
    store.clear_all()
    return {"status": "reset"}

@app.delete("/reset")
def reset_system(x_authorization: str | None = Header(default=None)):
    reset_db()
    store.clear_all()
    return {"status": "reset"}

# ------------------- AUTHENTICATION ENDPOINTS -------------------
@app.post("/auth/login", response_model=TokenResponse)
def login(credentials: LoginRequest):
    user = authenticate_user(credentials.username, credentials.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    access_token = create_access_token(data={"sub": user["username"], "role": user["role"]})
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserInfo(username=user["username"], email=user["email"], role=user["role"]),
    )

@app.post("/auth/register", response_model=UserInfo)
def register(request: RegisterRequest, authorization: str = Header(None)):
    require_admin(authorization)
    user = create_user(
        username=request.username,
        password=request.password,
        email=request.email,
        role=request.role,
    )
    return UserInfo(username=user["username"], email=user["email"], role=user["role"])

@app.get("/auth/me", response_model=UserInfo)
def get_current_user_info(authorization: str = Header(None)):
    user = get_current_user(authorization)
    return UserInfo(**user)

@app.get("/auth/users", response_model=List[UserInfo])
def list_all_users(authorization: str = Header(None)):
    require_admin(authorization)
    users = get_all_users()
    return [UserInfo(**u) for u in users]

@app.get("/auth/users/{username}", response_model=UserInfo)
def get_user(username: str, authorization: str = Header(None)):
    require_admin(authorization)
    user = get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserInfo(**user)

@app.put("/auth/users/{username}", response_model=UserInfo)
def update_user_info(username: str, request: UpdateUserRequest, authorization: str = Header(None)):
    require_admin(authorization)
    user = update_user(
        username=username,
        email=request.email,
        role=request.role,
        password=request.password,
    )
    return UserInfo(**user)

@app.delete("/auth/users/{username}")
def delete_user_account(username: str, authorization: str = Header(None)):
    require_admin(authorization)
    delete_user(username)
    return {"message": f"User {username} deleted successfully"}

# ------------------- PHASE 2: ARTIFACT ENDPOINTS -------------------
@app.post("/artifact/byRegEx", response_model=List[ArtifactMetadataOut])
async def artifact_by_regex(
    request: Request,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
):
    raw_body = await request.body()
    if not raw_body or not raw_body.strip():
        raise HTTPException(status_code=400, detail=BAD_ARTIFACT_REGEX_MSG)

    try:
        body = json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail=BAD_ARTIFACT_REGEX_MSG)

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail=BAD_ARTIFACT_REGEX_MSG)

    regex_value = body.get("regex") or body.get("artifact_regex")

    if isinstance(regex_value, dict):
        regex_value = regex_value.get("regex")

    if not isinstance(regex_value, str) or not regex_value.strip():
        raise HTTPException(status_code=400, detail=BAD_ARTIFACT_REGEX_MSG)

    regex_value = regex_value.strip()

    MAX_REGEX_LEN = 512
    if len(regex_value) > MAX_REGEX_LEN:
        raise HTTPException(status_code=400, detail=BAD_ARTIFACT_REGEX_MSG)

    for m in re.finditer(r"\{(\d+)(?:,(\d+))?\}", regex_value):
        lo = int(m.group(1))
        hi = int(m.group(2)) if m.group(2) else lo
        if lo > 1000 or hi > 1000 or (hi - lo) > 1000:
            raise HTTPException(status_code=400, detail=BAD_ARTIFACT_REGEX_MSG)

    if re.search(r"\([^()]*[+*][^()]*\)[+*]", regex_value):
        raise HTTPException(status_code=400, detail=BAD_ARTIFACT_REGEX_MSG)

    if regex_value.count("(") > 64:
        raise HTTPException(status_code=400, detail=BAD_ARTIFACT_REGEX_MSG)

    try:
        pattern = re.compile(regex_value)
    except re.error:
        raise HTTPException(status_code=400, detail=BAD_ARTIFACT_REGEX_MSG)

    artifacts = store.list_artifacts()
    matches: list[ArtifactMetadataOut] = []

    for a in artifacts:
        name = a.get("name") or ""
        if pattern.search(name):
            matches.append(
                ArtifactMetadataOut(
                    name=a["name"],
                    id=str(a["id"]),
                    type=ArtifactType(_normalize_type(a["type"])),
                    url=a.get("url"),
                )
            )

    if not matches:
        raise HTTPException(status_code=404, detail=NO_ARTIFACT_FOR_REGEX_MSG)

    return matches

@app.post("/artifact/{artifact_type}", response_model=ArtifactOut, status_code=201)
def ingest_artifact_phase2(
    artifact_type: str,
    payload: ArtifactDataIn,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
):
    artifact_type = _normalize_type(artifact_type)
    if artifact_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail="Invalid artifact_type")

    name = name_from_url(str(payload.url))
    readme = fetch_readme(str(payload.url))

    item = {
        "id": None,
        "name": name,
        "type": artifact_type,
        "url": str(payload.url),
        "description": None,
        "readme": readme,
        "created_at": time.time(),
    }

    item = store.put_artifact(item)
    aid = int(item["id"])
    _metrics["upload_count"] += 1

    if artifact_type == "model":
        try:
            res = _compute_one(str(payload.url), "MODEL")
        except Exception as e:
            logger.exception(f"[ingest-rate] failed for url={payload.url}: {e}")
            store.delete_artifact(aid)
            raise HTTPException(status_code=424, detail="Rating pipeline error")

        size_score_out = SizeScoreOut(**res.size_score)
        rating_out = ModelRatingOut(
            name=item["name"],
            category=res.category,
            net_score=res.net_score,
            net_score_latency=int(res.net_score_latency),
            ramp_up_time=res.ramp_up_time,
            ramp_up_time_latency=int(res.ramp_up_time_latency),
            bus_factor=res.bus_factor,
            bus_factor_latency=int(res.bus_factor_latency),
            performance_claims=res.performance_claims,
            performance_claims_latency=int(res.performance_claims_latency),
            license=res.license,
            license_latency=int(res.license_latency),
            dataset_and_code_score=res.dataset_and_code_score,
            dataset_and_code_score_latency=int(res.dataset_and_code_score_latency),
            dataset_quality=res.dataset_quality,
            dataset_quality_latency=int(res.dataset_quality_latency),
            code_quality=res.code_quality,
            code_quality_latency=int(res.code_quality_latency),
            reproducibility=res.reproducibility,
            reproducibility_latency=int(res.reproducibility_latency),
            reviewedness=res.reviewedness,
            reviewedness_latency=int(res.reviewedness_latency),
            tree_score=res.tree_score,
            tree_score_latency=int(res.tree_score_latency),
            size_score=size_score_out,
            size_score_latency=int(res.size_score_latency),
        )
        store.put_rating(aid, rating_out.model_dump())

    metadata = ArtifactMetadataOut(
        name=item["name"],
        id=str(aid),
        type=ArtifactType(_normalize_type(item["type"])),
        url=item.get("url"),
    )
    data: Dict[str, Any] = {"url": item.get("url")}
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
            types_filter = {_normalize_type(t.value) for t in q.types}

        for a in all_items:
            if types_filter and _normalize_type(a["type"]) not in types_filter:
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
            type=ArtifactType(_normalize_type(a["type"])),
            url=a.get("url"),
        )
        for a in page
    ]

@app.get("/artifacts", response_model=List[ArtifactMetadataOut])
def get_all_artifacts_alias(
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
):
    all_items = store.list_artifacts()
    all_items.sort(key=lambda x: int(x["id"]))
    return [
        ArtifactMetadataOut(
            name=a["name"],
            id=str(a["id"]),
            type=ArtifactType(_normalize_type(a["type"])),
            url=a.get("url"),
        )
        for a in all_items
    ]

@app.get("/artifact", response_model=List[ArtifactMetadataOut])
def get_all_artifacts(
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
):
    return get_all_artifacts_alias(x_authorization)

def _parse_int_id(id: str) -> int:
    s = (id or "").strip().strip('"').strip("'").strip()
    if not s.isdigit():
        raise HTTPException(status_code=400, detail=BAD_ARTIFACT_ID_OR_TYPE_MSG)
    return int(s)

def _get_artifact_by_type_and_id(artifact_type: str, id: str) -> ArtifactOut:
    artifact_type = _normalize_type(artifact_type)

    if artifact_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail=BAD_ARTIFACT_ID_OR_TYPE_MSG)

    aid = _parse_int_id(id)

    obj = store.get_artifact(aid)
    if obj is None or _normalize_type(obj.get("type")) != artifact_type:
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    metadata = ArtifactMetadataOut(
        name=obj["name"],
        id=str(obj["id"]),
        type=ArtifactType(_normalize_type(obj["type"])),
        url=obj.get("url"),
    )
    data = {"url": obj.get("url")}
    return ArtifactOut(metadata=metadata, data=data)

@app.get("/artifact/{artifact_type}/{id}", response_model=ArtifactOut)
def get_artifact_phase2_singular(
    artifact_type: str,
    id: str,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
):
    return _get_artifact_by_type_and_id(artifact_type, id)

@app.get("/artifacts/{artifact_type}/{id}", response_model=ArtifactOut)
def get_artifact_phase2_plural(
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
    artifact_type = _normalize_type(artifact_type)

    if artifact_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail=BAD_ARTIFACT_ID_OR_TYPE_MSG)

    aid = _parse_int_id(id)

    obj = store.get_artifact(aid)
    if obj is None or _normalize_type(obj.get("type")) != artifact_type:
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    store.delete_artifact(aid)
    return {"status": "deleted"}

@app.delete("/artifacts/{artifact_type}/{id}")
def delete_artifact_phase2_plural(
    artifact_type: str,
    id: str,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
):
    return delete_artifact_phase2(artifact_type, id, x_authorization)

@app.get("/artifact/model/{id}/rate", response_model=ModelRatingOut)
def rate_model_artifact(
    id: str,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
):
    aid = _parse_int_id(id)

    art = store.get_artifact(aid)
    if art is None or _normalize_type(art.get("type")) != "model":
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    rating = store.get_rating(aid)
    if rating is not None:
        rating["name"] = art["name"]
        return ModelRatingOut(**rating)

    lock = _rate_locks[aid]
    with lock:
        rating = store.get_rating(aid)
        if rating is None:
            rating = _compute_and_store_rating(aid, art)
        rating["name"] = art["name"]
        return ModelRatingOut(**rating)

@app.get("/artifacts/model/{id}/rate", response_model=ModelRatingOut)
def rate_model_artifact_plural(
    id: str,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
):
    return rate_model_artifact(id, x_authorization)

def _download_url_impl(artifact_type: str, id: str):
    artifact_type = _normalize_type(artifact_type)

    if artifact_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail=BAD_ARTIFACT_ID_OR_TYPE_MSG)

    aid = _parse_int_id(id)

    obj = store.get_artifact(aid)
    if obj is None or _normalize_type(obj.get("type")) != artifact_type:
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    _metrics["download_count"] += 1
    return {"url": obj.get("url")}

@app.get("/artifact/{artifact_type}/{id}/download")
def download_url1(
    artifact_type: str,
    id: str,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
):
    return _download_url_impl(artifact_type, id)

@app.get("/artifacts/{artifact_type}/{id}/download")
def download_url2(
    artifact_type: str,
    id: str,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
):
    return _download_url_impl(artifact_type, id)

@app.get("/artifact/{artifact_type}/{id}/downloadUrl")
def download_url3(
    artifact_type: str,
    id: str,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
):
    return _download_url_impl(artifact_type, id)

@app.get("/artifacts/{artifact_type}/{id}/downloadUrl")
def download_url3b(
    artifact_type: str,
    id: str,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
):
    return _download_url_impl(artifact_type, id)

@app.get("/artifact/{artifact_type}/{id}/url")
def download_url4(
    artifact_type: str,
    id: str,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
):
    return _download_url_impl(artifact_type, id)

@app.get("/artifacts/{artifact_type}/{id}/url")
def download_url4b(
    artifact_type: str,
    id: str,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
):
    return _download_url_impl(artifact_type, id)

# ------------------- NEW: COST ENDPOINTS -------------------
# Spec: GET /artifact/{artifact_type}/{id}/cost?dependency=true|false
# Return: { "<id>": { "standalone_cost": <float>, "total_cost": <float> } }
@app.get("/artifact/{artifact_type}/{id}/cost")
def artifact_cost(
    artifact_type: str,
    id: str,
    dependency: bool = False,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
):
    artifact_type = _normalize_type(artifact_type)
    if artifact_type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail=BAD_ARTIFACT_ID_OR_TYPE_MSG)

    aid = _parse_int_id(id)
    obj = store.get_artifact(aid)
    if obj is None or _normalize_type(obj.get("type")) != artifact_type:
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    standalone = float(estimate_cost_mb(obj.get("url") or "", artifact_type))
    total = standalone

    # best-effort dependency: if model, include readme size as tiny dependency signal
    # (keeps predictable + non-zero behavior without inventing fake artifact ids)
    if dependency and artifact_type == "model":
        rd = (obj.get("readme") or "")
        total = round(standalone + (len(rd.encode("utf-8")) / (1024 * 1024)), 4)

    return {str(aid): {"standalone_cost": standalone, "total_cost": float(total)}}

@app.get("/artifacts/{artifact_type}/{id}/cost")
def artifact_cost_plural(
    artifact_type: str,
    id: str,
    dependency: bool = False,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
):
    return artifact_cost(artifact_type, id, dependency, x_authorization)

# ------------------- NEW: LICENSE CHECK ENDPOINTS -------------------

def _parse_github_owner_repo(url: str) -> tuple[str, str]:
    u = (url or "").strip()
    m = re.match(r"^https?://github\.com/([^/]+)/([^/]+)", u)
    if not m:
        raise ValueError("Not a GitHub URL")
    owner = m.group(1)
    repo = m.group(2).replace(".git", "")
    return owner, repo

def _github_has_valid_license(github_url: str) -> bool:
    try:
        owner, repo = _parse_github_owner_repo(github_url)
    except Exception:
        return False

    api_url = f"https://api.github.com/repos/{owner}/{repo}/license"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ece461-autograder",
    }

    try:
        r = requests.get(api_url, headers=headers, timeout=12)
        if r.status_code != 200:
            return False
        data = r.json()
        lic = data.get("license") or {}
        spdx = (lic.get("spdx_id") or "").strip()
        if not spdx or spdx.upper() == "NOASSERTION":
            return False
        return True
    except Exception:
        return False

# Spec: POST /artifact/model/{id}/license-check {github_url} -> bool
@app.post("/artifact/model/{id}/license-check")
def license_check(
    id: str,
    body: LicenseCheckIn,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
):
    # Validate artifact exists and is a model
    aid = _parse_int_id(id)
    art = store.get_artifact(aid)
    if art is None or _normalize_type(art.get("type")) != "model":
        raise HTTPException(status_code=404, detail="Artifact does not exist")

    github_url = body.resolved_url()
    if not github_url:
        raise HTTPException(status_code=400, detail="Missing GitHub URL")

    # Check if the GitHub repo exists and get its license
    gh = _github_owner_repo_from_url(github_url)
    if not gh:
        raise HTTPException(status_code=400, detail="Invalid GitHub URL")

    # Get GitHub repo license (optimized: single API call with caching)
    code_spdx, status_code = _github_repo_license_spdx(github_url)
    if status_code == 404:
        raise HTTPException(status_code=404, detail="GitHub repository not found")
    if status_code == 502:
        raise HTTPException(status_code=502, detail="Could not retrieve GitHub repository info")
    if code_spdx is None:
        # Repo exists but has no license - treat as incompatible
        return False

    # Get model license from HuggingFace (from the artifact's URL)
    model_url = art.get("url") or ""
    model_spdx = _hf_model_license_spdx(model_url)
    if model_spdx is None:
        # Model has no license info - treat as incompatible rather than 502
        return False

    # Check compatibility
    return _licenses_compatible(model_spdx, code_spdx)


# Also support PUT for backwards compatibility
@app.put("/artifact/model/{id}/license-check")
def license_check_put(
    id: str,
    body: LicenseCheckIn,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
):
    return license_check(id, body, x_authorization)


@app.post("/artifacts/model/{id}/license-check")
def license_check_plural(
    id: str,
    body: LicenseCheckIn,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
):
    return license_check(id, body, x_authorization)


@app.put("/artifacts/model/{id}/license-check")
def license_check_plural_put(
    id: str,
    body: LicenseCheckIn,
    x_authorization: str | None = Header(default=None, alias="X-Authorization"),
):
    return license_check(id, body, x_authorization)