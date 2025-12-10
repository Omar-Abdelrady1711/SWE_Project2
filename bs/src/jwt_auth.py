# bs/src/auth.py
"""
Simple JWT-based authentication for the artifact registry.
In production, use proper password hashing (bcrypt) and secure secret management.
"""
import os
import time
import jwt
import bcrypt
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import HTTPException, Header

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Pre-computed password hashes using bcrypt directly
# These are bcrypt hashes of "admin123" and "user123"
ADMIN_PASSWORD_HASH = b'$2b$12$SEzE5hlA2RnXTPzUKEc2wuVLwoNyB8ABejWCtFbaNpQeWKXPyPFlW'  # admin123
USER_PASSWORD_HASH = b'$2b$12$T0qxhAKks2Ak0sjRMy1zhOuampHijddAdEuJkPn4K8uZrjS9.2qFq'   # user123

# In-memory user store (replace with DB in production)
USERS_DB: Dict[str, Dict[str, Any]] = {
    "admin": {
        "username": "admin",
        "hashed_password": ADMIN_PASSWORD_HASH,  # bytes
        "role": "admin",
        "email": "admin@example.com",
    },
    "user": {
        "username": "user",
        "hashed_password": USER_PASSWORD_HASH,  # bytes
        "role": "user",
        "email": "user@example.com",
    },
}


def verify_password(plain_password: str, hashed_password: bytes) -> bool:
    """Verify a plain password against a hashed password using bcrypt directly."""
    password_bytes = plain_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_password)


def get_password_hash(password: str) -> bytes:
    """Hash a password using bcrypt directly."""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password_bytes, salt)




def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate a user by username and password."""
    user = USERS_DB.get(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user


def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """
    Get the current authenticated user from the Authorization header.
    Expected format: "Bearer <token>"
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid authentication scheme")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    payload = decode_access_token(token)
    username = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    
    user = USERS_DB.get(username)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    return {
        "username": user["username"],
        "role": user["role"],
        "email": user["email"],
    }


def require_admin(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Require that the current user is an admin."""
    user = get_current_user(authorization)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def create_user(username: str, password: str, email: str, role: str = "user") -> Dict[str, Any]:
    """Create a new user (admin only operation)."""
    if username in USERS_DB:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    if role not in ["user", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    user = {
        "username": username,
        "hashed_password": get_password_hash(password),
        "role": role,
        "email": email,
    }
    USERS_DB[username] = user
    
    return {
        "username": user["username"],
        "role": user["role"],
        "email": user["email"],
    }


def get_all_users() -> list[Dict[str, Any]]:
    """Get all users (admin only operation)."""
    return [
        {
            "username": user["username"],
            "role": user["role"],
            "email": user["email"],
        }
        for user in USERS_DB.values()
    ]


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Get a specific user by username (admin only operation)."""
    user = USERS_DB.get(username)
    if not user:
        return None
    
    return {
        "username": user["username"],
        "role": user["role"],
        "email": user["email"],
    }


def update_user(username: str, email: Optional[str] = None, role: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
    """Update user information (admin only operation)."""
    if username not in USERS_DB:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = USERS_DB[username]
    
    if email is not None:
        user["email"] = email
    
    if role is not None:
        if role not in ["user", "admin"]:
            raise HTTPException(status_code=400, detail="Invalid role")
        user["role"] = role
    
    if password is not None:
        user["hashed_password"] = get_password_hash(password)
    
    return {
        "username": user["username"],
        "role": user["role"],
        "email": user["email"],
    }


def delete_user(username: str) -> bool:
    """Delete a user (admin only operation)."""
    if username not in USERS_DB:
        raise HTTPException(status_code=404, detail="User not found")
    
    if username == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete admin user")
    
    del USERS_DB[username]
    return True
