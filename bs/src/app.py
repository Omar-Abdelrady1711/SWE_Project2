from fastapi import FastAPI, APIRouter
from fastapi.responses import RedirectResponse
from fastapi.openapi.docs import get_swagger_ui_html
from mangum import Mangum
import os, time, logging
from typing import Dict, Any, Optional

STAGE = os.getenv("API_GATEWAY_BASE_PATH", "/Prod")

app = FastAPI(
    title="Team31 Backend (Phase 2)",
    docs_url=None,                        # <-- disable built-in docs
    redoc_url=None,
    openapi_url="/openapi.json",  # <-- OpenAPI served under the stage
    root_path=STAGE,                      # <-- tell FastAPI it's mounted at /Prod
)

api = APIRouter(prefix="/api")

@api.get("/health")
def api_health():
    return {"status": "ok", "phase": 2, "time": time.time()}

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
