from fastapi import FastAPI
from .db import init_db
from .crud import router as api_router
from . import mqtt_bridge
import os

app = FastAPI(title="Automatic Aquarium Backend")

app.include_router(api_router)


@app.on_event("startup")
def on_startup():
    init_db()
    # start mqtt bridge optionally if configured
    if os.environ.get("START_MQTT_BRIDGE", "false").lower() in ("1", "true", "yes"):
        mqtt_bridge.start_bridge()


@app.get("/health")
def health():
    return {"status": "ok"}
