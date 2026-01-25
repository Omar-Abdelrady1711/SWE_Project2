import sys
import pathlib
import pytest
from fastapi.testclient import TestClient

# ensure project root is on sys.path so `backend` package imports work during test
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.app.main import app


def test_register_token_and_protected():
    with TestClient(app) as client:
        r = client.post("/auth/register", params={"username": "admin", "password": "secret", "roles": "admin"})
        assert r.status_code == 200

        r2 = client.post("/auth/token", params={"username": "admin", "password": "secret"})
        assert r2.status_code == 200
        data = r2.json()
        assert "access_token" in data and "refresh_token" in data
        access = data["access_token"]

        headers = {"Authorization": f"Bearer {access}"}
        r3 = client.get("/auth/protected-admin", headers=headers)
        assert r3.status_code == 200

        r4 = client.get("/auth/whoami", headers=headers)
        assert r4.status_code == 200
        assert r4.json()["username"] == "admin"
