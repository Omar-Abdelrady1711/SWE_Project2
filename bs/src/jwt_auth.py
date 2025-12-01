# bs/src/jwt_auth.py
"""
JWT-based authentication for the artifact registry with PostgreSQL persistence.
Uses bcrypt for secure password hashing.
"""
import os
import time
import jwt
import bcrypt
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import HTTPException, Header, Depends
from sqlalchemy.orm import Session
from bs.src.models_db import get_session, UserModel

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Pre-computed password hashes using bcrypt directly
# These are bcrypt hashes of "admin123" and "user123"
ADMIN_PASSWORD_HASH = '$2b$12$SEzE5hlA2RnXTPzUKEc2wuVLwoNyB8ABejWCtFbaNpQeWKXPyPFlW'  # admin123
USER_PASSWORD_HASH = '$2b$12$T0qxhAKks2Ak0sjRMy1zhOuampHijddAdEuJkPn4K8uZrjS9.2qFq'   # user123


def init_default_users(db: Session) -> None:
    """Initialize default admin and user accounts if they don't exist."""
    # Check if admin exists
    admin = db.query(UserModel).filter(UserModel.username == "admin").first()
    if not admin:
        admin_user = UserModel(
            username="admin",
            email="admin@example.com",
            hashed_password=ADMIN_PASSWORD_HASH,
            role="admin",
            is_active=True
        )
        db.add(admin_user)
    
    # Check if default user exists
    user = db.query(UserModel).filter(UserModel.username == "user").first()
    if not user:
        default_user = UserModel(
            username="user",
            email="user@example.com",
            hashed_password=USER_PASSWORD_HASH,
            role="user",
            is_active=True
        )
        db.add(default_user)
    
    db.commit()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password using bcrypt directly."""
    password_bytes = plain_password.encode('utf-8')
    # Handle both string and bytes hashed passwords
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt directly."""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')  # Store as string in database


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


def authenticate_user(username: str, password: str, db: Session) -> Optional[Dict[str, Any]]:
    """Authenticate a user by username and password."""
    user = db.query(UserModel).filter(UserModel.username == username).first()
    if not user:
        return None
    if not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    
    return {
        "username": user.username,
        "email": user.email,
        "role": user.role,
    }


def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_session)) -> Dict[str, Any]:
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
    
    user = db.query(UserModel).filter(UserModel.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    if not user.is_active:
        raise HTTPException(status_code=401, detail="User is inactive")
    
    return {
        "username": user.username,
        "role": user.role,
        "email": user.email,
    }


def require_admin(authorization: Optional[str] = Header(None), db: Session = Depends(get_session)) -> Dict[str, Any]:
    """Require that the current user is an admin."""
    user = get_current_user(authorization, db)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def create_user(username: str, password: str, email: str, role: str, db: Session) -> Dict[str, Any]:
    """Create a new user (admin only operation)."""
    # Check if username already exists
    existing_user = db.query(UserModel).filter(UserModel.username == username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Check if email already exists
    if email:
        existing_email = db.query(UserModel).filter(UserModel.email == email).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already exists")
    
    if role not in ["user", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    # Create new user
    new_user = UserModel(
        username=username,
        hashed_password=get_password_hash(password),
        role=role,
        email=email,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "username": new_user.username,
        "role": new_user.role,
        "email": new_user.email,
    }


def get_all_users(db: Session) -> list[Dict[str, Any]]:
    """Get all users (admin only operation)."""
    users = db.query(UserModel).all()
    return [
        {
            "username": user.username,
            "role": user.role,
            "email": user.email,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        }
        for user in users
    ]


def get_user_by_username(username: str, db: Session) -> Optional[Dict[str, Any]]:
    """Get a specific user by username (admin only operation)."""
    user = db.query(UserModel).filter(UserModel.username == username).first()
    if not user:
        return None
    
    return {
        "username": user.username,
        "role": user.role,
        "email": user.email,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def update_user(username: str, db: Session, email: Optional[str] = None, role: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
    """Update user information (admin only operation)."""
    user = db.query(UserModel).filter(UserModel.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if email is not None:
        # Check if email is already taken by another user
        existing_email = db.query(UserModel).filter(
            UserModel.email == email,
            UserModel.username != username
        ).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already exists")
        user.email = email
    
    if role is not None:
        if role not in ["user", "admin"]:
            raise HTTPException(status_code=400, detail="Invalid role")
        user.role = role
    
    if password is not None:
        user.hashed_password = get_password_hash(password)
    
    db.commit()
    db.refresh(user)
    
    return {
        "username": user.username,
        "role": user.role,
        "email": user.email,
    }


def delete_user(username: str, db: Session) -> bool:
    """Delete a user (admin only operation)."""
    user = db.query(UserModel).filter(UserModel.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if username == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete admin user")
    
    db.delete(user)
    db.commit()
    return True
