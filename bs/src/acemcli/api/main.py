# bs/src/acemcli/api/main.py
from fastapi import FastAPI
from mangum import Mangum

app = FastAPI(
    title="ACME Trustworthy Model Registry",
    version="0.1.0",
    description="Backend API for CRUD, ingest, and model scoring"
)

@app.get("/")
def root():
    return {"message": "ACME Trustworthy Model Registry API is running"}
@app.get("/health")
def health():
    """Simple health check for CI/CD smoke tests"""
    return {"status": "ok"}


# AWS Lambda entry point
lambda_handler = Mangum(app)
