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


def ensure_admin(db):
    admin = auth_crud.get_user_by_username(db, "admin")
    if not admin:
        admin = auth_crud.create_user(db, username="admin", email=None, password="adminpass", role="admin")
    return admin


def test_admin_creates_user_and_user_ingest_decrements_token():
    db = models_db.SessionLocal()
    ensure_admin(db)

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


def test_user_can_delete_self():
    db = models_db.SessionLocal()
    ensure_admin(db)

    # create user via admin
    r = client.post("/api/auth/login", json={"username": "admin", "password": "adminpass"})
    assert r.status_code == 200
    admin_token = r.json()["access_token"]
    headers = {"X-Authorization": admin_token}
    new_user = {"username": "deleteme", "password": "delpass", "email": "del@example.com"}
    r = client.post("/api/auth/admin/users", json=new_user, headers=headers)
    assert r.status_code == 200

    # login as the new user
    r = client.post("/api/auth/login", json={"username": "deleteme", "password": "delpass"})
    assert r.status_code == 200
    user_token = r.json()["access_token"]

    # delete self
    r = client.delete("/api/auth/users/me", headers={"X-Authorization": user_token})
    assert r.status_code == 200

    # ensure user no longer present
    db2 = models_db.SessionLocal()
    assert auth_crud.get_user_by_username(db2, "deleteme") is None
    db2.close()
    db.close()


def test_non_admin_cannot_create_user():
    db = models_db.SessionLocal()
    ensure_admin(db)

    # create a non-admin user directly
    user = auth_crud.get_user_by_username(db, "charlie")
    if not user:
        user = auth_crud.create_user(db, username="charlie", email=None, password="charliepass", role="user")

    # login as charlie
    r = client.post("/api/auth/login", json={"username": "charlie", "password": "charliepass"})
    assert r.status_code == 200
    token = r.json()["access_token"]

    # attempt to create a user using charlie's token
    headers = {"X-Authorization": token}
    new_user = {"username": "victim", "password": "vpass", "email": "v@example.com"}
    r = client.post("/api/auth/admin/users", json=new_user, headers=headers)
    # expect 403 Forbidden
    assert r.status_code == 403 or r.status_code == 401

    db.close()
