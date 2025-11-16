import os
import hashlib
from datetime import datetime, timedelta
from jose import jwt, JWTError
from typing import List

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
ALGORITHM = os.environ.get("ALGORITHM", "HS256")
ACCESS_EXPIRE_MIN = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_EXPIRE_DAYS = int(os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS", "30"))


def hash_password(password: str) -> str:
    # lightweight PBKDF2-based hash for example purposes (not argon2)
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return salt.hex() + "$" + dk.hex()


def verify_password(plain: str, stored: str) -> bool:
    try:
        salt_hex, dk_hex = stored.split("$")
        salt = bytes.fromhex(salt_hex)
        dk_check = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt, 100_000)
        return dk_check.hex() == dk_hex
    except Exception:
        return False


def create_access_token(subject: str, roles: List[str]) -> str:
    now = datetime.utcnow()
    payload = {
        "sub": subject,
        "roles": roles,
        "iat": now.timestamp(),
        "exp": (now + timedelta(minutes=ACCESS_EXPIRE_MIN)).timestamp(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(subject: str) -> str:
    now = datetime.utcnow()
    payload = {
        "sub": subject,
        "iat": now.timestamp(),
        "exp": (now + timedelta(days=REFRESH_EXPIRE_DAYS)).timestamp(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise
