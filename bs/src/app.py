# bs/src/app.py
from fastapi import FastAPI, APIRouter
from fastapi.responses import RedirectResponse

app = FastAPI(title="Team31 Backend")

# ---- define an API router that lives under /api ----
api = APIRouter(prefix="/api")

@api.get("/health")
def health():
    return {"status": "ok"}

@api.get("/")
def api_root():
    return {"message": "Backend running!", "docs": "/api/docs"}

# If your feature routers exist, include them *under* /api
# Example (adjust to your actual names):
# from src.api.routes.artifacts import router as artifacts_router
# api.include_router(artifacts_router)  # keep their own paths like /artifacts, /search, etc.

# finally mount /api onto the app
app.include_router(api)

# optional: make / redirect to /api
@app.get("/")
def root():
    return RedirectResponse(url="/api")
