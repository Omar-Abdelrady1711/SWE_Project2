from fastapi import FastAPI, APIRouter, Header
from fastapi.responses import RedirectResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import os
import time
import logging

from bs.src.models_db import init_db, reset_db

# Define which frontend origins are allowed to call this backend
origins = [
    "http://localhost:5173",  # local dev
    "https://z7rple5yzi.execute-api.us-east-1.amazonaws.com",  # deployed frontend URL
]

STAGE = os.getenv("API_GATEWAY_BASE_PATH", "/Prod")

app = FastAPI(
    title="Team31 Backend (Phase 2)",
    docs_url=None,  # <-- disable built-in docs
    redoc_url=None,
    openapi_url="/openapi.json",
    root_path=STAGE,  # <-- tell FastAPI it's mounted at /Prod
)

# CORS middleware
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


# (safe-load your DB router exactly as you had)
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


@app.get("/tracks")
def get_tracks():
    # We are not doing any special track yet, so just return empty list.
    return {"plannedTracks": []}


@app.delete("/reset")
def reset_system(x_authorization: str | None = Header(default=None)):
    """
    Reset the registry to an empty state.
    Ignore X-Authorization for now (no access-control track).
    """
    reset_db()
    return {"status": "reset"}


handler = Mangum(app, api_gateway_base_path=STAGE)
