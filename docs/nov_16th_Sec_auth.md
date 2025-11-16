**Nov 16th — Auth Implementation Notes**

Summary
-------
On Nov 16 I added a minimal authentication example to the `backend/` scaffold to demonstrate token handling and role-based permissions (Person A scope). The implementation is intentionally small and suitable for iterative improvement; it includes JWT token creation, a simple refresh flow, role enforcement dependency, and tests that exercise registration, login, and a protected endpoint.

- `backend/requirements.txt` — added test and auth deps (`passlib` was added then removed in favor of a deterministic PBKDF2 helper; final requirements include `python-jose`, `pytest`, and test helpers).
- `backend/__init__.py` — make `backend` importable by tests.
- `backend/app/models.py` — added `User` and `RefreshToken` SQLModel models (in addition to the previously created domain models).
- `backend/app/db.py` — now imports `models` to ensure SQLModel metadata is registered before creating tables.
- `backend/app/auth.py` — auth helpers:
  - PBKDF2-based password hashing (example implementation) with verify helper
  - JWT helpers: `create_access_token`, `create_refresh_token`, `decode_token`
  - Note: PBKDF2 was chosen here to avoid bcrypt/build issues in the test environment; for production use Argon2 or bcrypt via `passlib`.
- `backend/app/deps.py` — FastAPI dependencies:
  - `get_current_user` (HTTP Bearer token parsing + JWT decode)
  - `require_role(role)` (dependency that enforces role membership on routes)
- `backend/app/routes/auth.py` — auth endpoints:
  - `POST /auth/register` — create user (plain params for example)
  - `POST /auth/token` — exchange username/password for access+refresh tokens
  - `POST /auth/refresh` — exchange refresh token for new access token
  - `GET /auth/protected-admin` — example protected endpoint (requires `admin` role)
  - `GET /auth/whoami` — returns token subject and roles
- `backend/tests/test_auth.py` — integration test using `TestClient` that registers a user, requests tokens, and accesses protected endpoints

What I changed
- Registered the auth router in `backend/app/main.py`.
- Updated `backend/app/models.py` to include `User` and `RefreshToken`.
- Added `backend/app/mqtt_bridge.py` earlier (unrelated to auth) and left it as a lightweight example.
- `backend/app/db.py` was modified to import models so `SQLModel.metadata.create_all()` sees the tables.

How the auth works (design notes)
- Access tokens: JWT (HS256) with `sub` and `roles` claims. Short-lived by default (configurable via env var `ACCESS_TOKEN_EXPIRE_MINUTES`).
- Refresh tokens: JWT with longer lifetime. In this example the refresh token is stored in the DB (as `token_hash` for simplicity) so it can be revoked.
- Password storage: example uses PBKDF2-HMAC-SHA256 with per-user random salt, stored as `salt$derivedhex`. This is safe for an example but for production prefer Argon2 or passlib-managed bcrypt/argon2.
- Role enforcement: `require_role("admin")` dependency decodes JWT and verifies the `roles` claim contains the required role.

Run & test (local)
1. Create/activate venv (PowerShell):

```powershell
Set-Location "C:\Users\~Lucas~\Desktop\github folder\SWE_Project2"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

2. Run the app:

```powershell
uvicorn backend.app.main:app --reload --port 8000
# API docs: http://127.0.0.1:8000/docs
```

3. Run tests (I ran this locally during development):

```powershell
.\.venv\Scripts\Activate.ps1
pytest -q backend/tests/test_auth.py::test_register_token_and_protected
```

Notes from the test run & environment adjustments
- Initially I added `passlib[bcrypt]`, but bcrypt/backends caused errors in the environment (bcrypt backend version detection and bcrypt length limits). To keep the example reliable for local runs and CI, I replaced passlib usage with a simple PBKDF2 helper in `auth.py`. If you prefer bcrypt/argon2, we can reintroduce `passlib` and ensure the CI environment includes the needed binary wheels.
- SQLite DB tables are created on app startup via `init_db()` in `backend/app/db.py`. Tests use `TestClient(app)` as a context manager so startup handlers run and create tables before tests execute.
- Tests currently store refresh tokens verbatim in the DB for simplicity; in production store a hash and rotate refresh tokens on use.

Security cautions
- Do not commit `SECRET_KEY` to source. Set `SECRET_KEY` via environment variables or a secret manager for deploys.
- Use HTTPS in production and shorter access token expiration; refresh tokens should be protected and rotated.
- Avoid storing raw refresh tokens in DB in production; store a hash or use opaque tokens.

Next recommended steps
- Implement refresh-token hashing and rotation (revoke old refresh tokens on refresh).
- Replace PBKDF2 helper with `passlib` + `argon2` (or bcrypt) for stronger password hashing.
- Add user management endpoints (list users, delete, update roles) and seed an initial admin user in DB migrations.
- Add API key or OAuth2 flows if you expect machine-to-machine or 3rd-party integration.
- Add tests for refresh/revoke functionality and add CI workflow to run tests on push.
