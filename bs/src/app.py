from fastapi import FastAPI
from src.api.routes.artifacts import router as artifacts_router
# (if you have other routers, do the same idea)

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Backend running!", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "ok"}

# give a non-empty prefix
app.include_router(artifacts_router, prefix="/artifacts", tags=["artifacts"])
