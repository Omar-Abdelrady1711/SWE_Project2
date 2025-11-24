from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from .deps import get_db, get_current_user
from . import crud


def require_role(role: str):
    def _role_checker(current=Depends(get_current_user)):
        user = current["user"]
        if user.role != role:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return current
    return _role_checker


def require_permission(permission: str):
    """Check token remaining_calls and optionally role-based permission.

    For now admin bypasses checks; regular users must have remaining_calls>0.
    """
    def _perm(current=Depends(get_current_user), db: Session = Depends(get_db)):
        user = current["user"]
        token = current["token"]
        if user.role == "admin":
            return current
        # For regular users ensure the token has calls remaining
        if token.revoked:
            raise HTTPException(status_code=401, detail="Token revoked")
        if token.expires_at < datetime.utcnow():
            raise HTTPException(status_code=401, detail="Token expired")
        if token.remaining_calls <= 0:
            raise HTTPException(status_code=429, detail="API call limit exceeded")
        # decrement
        crud.decrement_token_call(db, token)
        return current
    return _perm
