## Nov 23 - Authentication & Authorization changes

Summary of changes made on 2025-11-23:

- Added a new `bs/src/auth` package with the following modules:
  - `models.py` - SQLAlchemy models for `User` and `Token`.
  - `schemas.py` - Pydantic request/response models for auth endpoints.
  - `security.py` - Argon2 password hashing (via `passlib`) and JWT helpers (via `python-jose`).
  - `crud.py` - Database helper functions for users and tokens.
  - `deps.py` - FastAPI dependencies to load current user from token.
  - `permissions.py` - Role and permission dependency factories that decrement token call counts.
  - `routes.py` - Auth endpoints: `POST /auth/login`, `POST /auth/logout`, `DELETE /auth/users/me`, and `POST /auth/admin/users` (admin-only).

- Updated `bs/src/app.py` to import auth models before DB initialization so tables are created, and to include the auth routers under `/api` when available.

- Added a simple SQL creation script at `bs/migrations/create_auth_tables.sql` for SQLite to create the `users` and `tokens` tables.

- Appended required packages to `requirements.txt`: `passlib[argon2]`, `python-jose[cryptography]`, `cryptography`, and `argon2-cffi`.

Design notes and decisions:

User Registration: Implemented (admin-only). Integration-tested for admin→create-user flow. DELETE self implemented (not explicitly covered by tests, can add).
User Login: Implemented. Integration-tested (admin and regular user logins passed).
Password Hashing: Implemented with Argon2 (passlib + argon2-cffi). Verified indirectly by login tests.
JWT Token Generation: Implemented (10-hour default expiry; jti; DB record with 1000 calls). Tested (token presence, DB record, jti decode).
Role-Based Permissions: Implemented. Partially tested (upload permission decremented on /api/ingest and logout revocation tested). Needs broader tests for search/download and concurrency-hardening for production.