import os
from datetime import datetime, timedelta
from typing import Dict, Any
import uuid

from passlib.context import CryptContext
from jose import jwt, JWTError

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
DEFAULT_EXPIRE_HOURS = int(os.getenv("TOKEN_EXP_HOURS", "10"))

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_jti() -> str:
    return str(uuid.uuid4())


def create_access_token(data: Dict[str, Any], expires_hours: int | None = None, jti: str | None = None) -> str:
    to_encode = data.copy()
    now = datetime.utcnow()
    expire = now + timedelta(hours=(expires_hours or DEFAULT_EXPIRE_HOURS))
    to_encode.update({"exp": expire, "iat": now, "jti": jti or create_jti()})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise
