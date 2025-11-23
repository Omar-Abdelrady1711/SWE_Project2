from datetime import datetime
from sqlalchemy.orm import Session

from . import models
from .security import get_password_hash


def create_user(db: Session, username: str, email: str | None, password: str, role: str = "user") -> models.User:
    hashed = get_password_hash(password)
    user = models.User(username=username, email=email, hashed_password=hashed, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()


def get_user_by_id(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def delete_user(db: Session, user: models.User):
    # Remove any tokens associated with this user first to avoid FK/NULL issues
    db.query(models.Token).filter(models.Token.user_id == user.id).delete()
    db.delete(user)
    db.commit()


def create_token_record(db: Session, user_id: int, jti: str, issued_at: datetime, expires_at: datetime, remaining_calls: int = 1000):
    token = models.Token(user_id=user_id, jti=jti, issued_at=issued_at, expires_at=expires_at, remaining_calls=remaining_calls)
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def get_token_by_jti(db: Session, jti: str):
    return db.query(models.Token).filter(models.Token.jti == jti).first()


def revoke_token(db: Session, token: models.Token):
    token.revoked = True
    db.add(token)
    db.commit()


def decrement_token_call(db: Session, token: models.Token) -> int:
    # Use a transaction to avoid races
    if token.remaining_calls <= 0:
        return 0
    token.remaining_calls = token.remaining_calls - 1
    db.add(token)
    db.commit()
    db.refresh(token)
    return token.remaining_calls
