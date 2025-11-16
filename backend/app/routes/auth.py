from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from ..db import get_session
from ..models import User, RefreshToken
from ..auth import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from ..deps import require_role, get_current_user
from datetime import datetime

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
def register(username: str, password: str, roles: str = "user", session=Depends(get_session)):
    stmt = select(User).where(User.username == username)
    existing = session.exec(stmt).first()
    if existing:
        raise HTTPException(status_code=400, detail="User exists")
    user = User(username=username, password_hash=hash_password(password), roles=roles)
    session.add(user)
    session.commit()
    session.refresh(user)
    return {"id": user.id, "username": user.username}


@router.post("/token")
def token(username: str, password: str, session=Depends(get_session)):
    stmt = select(User).where(User.username == username)
    user = session.exec(stmt).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    roles = (user.roles or "").split(",") if user.roles else []
    access = create_access_token(user.username, roles)
    refresh = create_refresh_token(user.username)
    # store refresh token hash (simple storage: store token itself for example purposes)
    rt = RefreshToken(user_id=user.id, token_hash=refresh, issued_at=datetime.utcnow())
    session.add(rt)
    session.commit()
    return {"access_token": access, "refresh_token": refresh}


@router.post("/refresh")
def refresh(refresh_token: str, session=Depends(get_session)):
    try:
        payload = decode_token(refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    username = payload.get("sub")
    stmt = select(User).where(User.username == username)
    user = session.exec(stmt).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    # find stored token
    stmt2 = select(RefreshToken).where(RefreshToken.token_hash == refresh_token, RefreshToken.revoked == False)
    rt = session.exec(stmt2).first()
    if not rt:
        raise HTTPException(status_code=401, detail="Refresh token revoked or not found")
    # issue new access token
    roles = (user.roles or "").split(",") if user.roles else []
    access = create_access_token(user.username, roles)
    return {"access_token": access}


@router.get("/protected-admin")
def protected_admin(user=Depends(require_role("admin"))):
    return {"ok": True, "user": user}


@router.get("/whoami")
def whoami(user=Depends(get_current_user)):
    return user
