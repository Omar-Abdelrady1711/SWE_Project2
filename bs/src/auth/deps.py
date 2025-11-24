from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from bs.src.models_db import get_session
from . import crud, security


def get_db():
    yield from get_session()


def get_current_user(x_authorization: str | None = Header(default=None, alias="X-Authorization"), db: Session = Depends(get_db)):
    if x_authorization is None:
        raise HTTPException(status_code=401, detail="Missing auth token")
    token_str = x_authorization
    try:
        payload = security.decode_token(token_str)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = payload.get("sub") or payload.get("user_id")
    jti = payload.get("jti")
    if not user_id or not jti:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    user = crud.get_user_by_id(db, int(user_id))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    # Check token exists and not revoked/expired
    token = crud.get_token_by_jti(db, jti)
    if not token or token.revoked:
        raise HTTPException(status_code=401, detail="Token revoked or not recognized")
    if token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Token expired")
    # Return tuple for downstream deps: (user, token)
    return {"user": user, "token": token}
