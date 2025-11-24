from fastapi.testclient import TestClient
from bs.src.app import app

from bs.src import models_db
from bs.src.auth import crud as auth_crud
from bs.src.auth import security as auth_security


client = TestClient(app)


def setup_module(module):
    # Ensure a clean DB for tests
    models_db.reset_db()
    models_db.init_db()


def test_admin_creates_user_and_user_ingest_decrements_token():
    db = models_db.SessionLocal()

    # create an admin user directly in DB
    admin = auth_crud.create_user(db, username="admin", email=None, password="adminpass", role="admin")

    # admin login
    r = client.post("/api/auth/login", json={"username": "admin", "password": "adminpass"})
    assert r.status_code == 200, r.text
    admin_token = r.json()["access_token"]

    # admin creates a regular user via API
    headers = {"X-Authorization": admin_token}
    new_user = {"username": "bob", "password": "bobpass", "email": "bob@example.com"}
    r = client.post("/api/auth/admin/users", json=new_user, headers=headers)
    assert r.status_code == 200, r.text

    # login as bob
    r = client.post("/api/auth/login", json={"username": "bob", "password": "bobpass"})
    assert r.status_code == 200, r.text
    bob_token = r.json()["access_token"]
    # decode token to get jti
    payload = auth_security.decode_token(bob_token)
    jti = payload.get("jti")
    assert jti is not None

    # call ingest endpoint which requires 'upload' permission and should decrement remaining_calls
    headers = {"X-Authorization": bob_token}
    payload = {"type": "model", "name": "somename"}
    r = client.post("/api/ingest", json=payload, headers=headers)
    assert r.status_code == 201, r.text

    # check token record in DB
    token_rec = auth_crud.get_token_by_jti(db, jti)
    assert token_rec is not None
    assert token_rec.remaining_calls == 999

    # logout (revoke)
    r = client.post("/api/auth/logout", headers={"X-Authorization": bob_token})
    assert r.status_code == 200
    # use a fresh DB session to observe the committed change
    db2 = models_db.SessionLocal()
    token_rec2 = auth_crud.get_token_by_jti(db2, jti)
    assert token_rec2 is not None
    assert token_rec2.revoked is True
    db2.close()

    db.close()
