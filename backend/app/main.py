from fastapi import FastAPI
from .db import init_db
from .crud import router as api_router
from .routes import auth as auth_routes
import os

app = FastAPI(title="Automatic Aquarium Backend")

app.include_router(api_router)
app.include_router(auth_routes.router)


@app.on_event("startup")
def on_startup():
    # Initialize database and other startup tasks
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}
