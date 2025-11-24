from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from . import schemas, crud, security
from .deps import get_db, get_current_user
from .permissions import require_role

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=schemas.LoginResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = crud.get_user_by_username(db, payload.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not security.verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    jti = security.create_jti()
    now = datetime.utcnow()
    expires = now + timedelta(hours=security.DEFAULT_EXPIRE_HOURS)
    token_data = {"sub": str(user.id), "username": user.username, "role": user.role}
    token_str = security.create_access_token(token_data, expires_hours=security.DEFAULT_EXPIRE_HOURS, jti=jti)
    # Persist token record
    token = crud.create_token_record(db, user_id=user.id, jti=jti, issued_at=now, expires_at=expires)
    return schemas.LoginResponse(access_token=token_str, expires_at=expires, remaining_calls=token.remaining_calls)


@router.post("/logout")
def logout(current=Depends(get_current_user), db: Session = Depends(get_db)):
    token = current["token"]
    crud.revoke_token(db, token)
    return {"status": "ok"}


admin_router = APIRouter(prefix="/admin", tags=["admin"])


@admin_router.post("/users", dependencies=[Depends(require_role("admin"))])
def admin_create_user(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = crud.get_user_by_username(db, payload.username)
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    user = crud.create_user(db, username=payload.username, email=payload.email, password=payload.password, role=payload.role)
    return {"id": user.id, "username": user.username}


@router.delete("/users/me")
def delete_me(current=Depends(get_current_user), db: Session = Depends(get_db)):
    user = current["user"]
    crud.delete_user(db, user)
    return {"status": "deleted"}
