# bs/src/app.py
from fastapi import FastAPI, APIRouter
from fastapi.responses import RedirectResponse
from typing import Dict, Any, List
import time
import re
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import logging

app = FastAPI(title="Team31 Backend (Phase 2)")
api = APIRouter(prefix="/api")

logger = logging.getLogger("requestlog")

class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.info(f">>> {request.method} {request.url.path}?{request.url.query}")
        response = await call_next(request)
        logger.info(f"<<< {response.status_code} {request.url.path}")
        return response

app.add_middleware(RequestLogMiddleware)

# ----------------------------
# In-memory store (ok for Render single process)
# ----------------------------
STORE: Dict[str, Any] = {
    "artifacts": [],  # list of dicts: {"id": int, "name": str, "type": "model|dataset|code", ...}
    "_next_id": 1,
}

# ----------------------------
# System endpoints
# ----------------------------
@api.get("/health")
def health():
    return {"status": "ok", "phase": 2, "time": time.time()}

@api.get("/tracks")
def tracks():
    # Access control track is optional; include it for visibility/tracking.
    return {"tracks": ["system", "artifacts", "regex", "read", "access_control"]}

@api.post("/reset")
def reset():
    STORE["artifacts"].clear()
    STORE["_next_id"] = 1
    return {"message": "reset-complete", "count": 0}

# optional: make "/" redirect to docs under /api
@api.get("/")
def api_root():
    return {"message": "Backend running", "docs": "/api/docs"}

app.include_router(api)

@app.get("/")
def root():
    return RedirectResponse(url="/api")
