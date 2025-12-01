# PostgreSQL User Storage Migration

## Overview

User authentication has been migrated from in-memory storage to **PostgreSQL database** for persistence.

## What Changed

### Before (In-Memory)

- Users stored in `USERS_DB` dictionary
- Lost on backend restart
- Only admin and user accounts
- Not shared across instances

### After (PostgreSQL)

- Users stored in `users` table
- **Persistent** across restarts
- Admin can create/edit/delete users
- Shared across all backend instances
- Supports multiple fields: `is_active`, `created_at`

## Database Schema

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT UNIQUE,
    hashed_password TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## Files Modified

### Core Changes

1. **`bs/src/models_db.py`**

   - Added `UserModel` SQLAlchemy model
   - Added `DateTime` and `Boolean` column types

2. **`bs/src/jwt_auth.py`**

   - Replaced `USERS_DB` dict with database queries
   - Added `init_default_users()` to create admin/user on startup
   - Updated all functions to accept `db: Session` parameter
   - Changed password hashes from `bytes` to `str` for database storage

3. **`bs/src/app.py`**

   - Updated all auth endpoints to inject `db: Session` via `Depends(get_session)`
   - Added default user initialization on startup
   - Added database session management

4. **`bs/src/auth_schemas.py`**
   - Added `is_active` and `created_at` fields to `UserInfo`

## Default Users

The system automatically creates these users on first startup:

| Username | Password | Role  | Email             |
| -------- | -------- | ----- | ----------------- |
| admin    | admin123 | admin | admin@example.com |
| user     | user123  | user  | user@example.com  |

## Database Configuration

The database uses the `DATABASE_URL` environment variable:

```bash
# Default (SQLite)
DATABASE_URL=sqlite:///tmp/registry.db

# PostgreSQL (recommended for production)
DATABASE_URL=postgresql://username:password@localhost:5432/dbname
```

## Migration Steps

1. **Backup existing data** (if needed)

   - In-memory users are recreated automatically

2. **Install dependencies** (already in requirements.txt)

   ```bash
   pip install sqlalchemy psycopg2-binary
   ```

3. **Set DATABASE_URL** (optional - defaults to SQLite)

   ```bash
   export DATABASE_URL=postgresql://user:pass@localhost:5432/registry
   ```

4. **Restart backend**

   ```bash
   python -m uvicorn bs.src.app:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Verify default users created**
   - Login as `admin/admin123`
   - Navigate to User Management page
   - See admin and user in the table

## Testing the Migration

### 1. Test Login

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

### 2. Create a New User

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"username":"testuser","password":"test123","email":"test@example.com","role":"user"}'
```

### 3. Restart Backend and Verify Persistence

```bash
# Stop backend (Ctrl+C)
# Start backend again
python -m uvicorn bs.src.app:app --reload --host 0.0.0.0 --port 8000

# Login with the new user you created
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"test123"}'
```

## Features Now Available

✅ **User Persistence** - Survives backend restarts  
✅ **CRUD Operations** - Create, read, update, delete users  
✅ **Email Tracking** - Unique email per user  
✅ **Active Status** - Enable/disable users (future feature)  
✅ **Creation Timestamps** - Track when users were created  
✅ **Scalability** - Multiple backend instances share same database

## API Endpoints

All endpoints support database-backed users:

- `POST /auth/login` - Login with username/password
- `POST /auth/register` - Create new user (admin-only)
- `GET /auth/me` - Get current user info
- `GET /auth/users` - List all users (admin-only)
- `GET /auth/users/{username}` - Get specific user (admin-only)
- `PUT /auth/users/{username}` - Update user (admin-only)
- `DELETE /auth/users/{username}` - Delete user (admin-only)

## Rollback (if needed)

If you need to rollback to in-memory storage, revert these commits:

```bash
git revert HEAD
```

## Production Recommendations

1. **Use PostgreSQL** instead of SQLite

   ```bash
   export DATABASE_URL=postgresql://user:pass@host:5432/dbname
   ```

2. **Environment Variables**

   - Set `JWT_SECRET_KEY` to a secure random value
   - Use connection pooling for PostgreSQL

3. **Database Backups**

   - Regular backups of `users` table
   - Export user data periodically

4. **Security**
   - Change default passwords immediately
   - Use strong JWT secret in production
   - Enable SSL for database connections

## Support

Default users are automatically created on startup. If you need to reset:

1. Delete the database file (SQLite): `rm /tmp/registry.db`
2. Restart backend - default users recreated automatically
