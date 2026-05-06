from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import RefreshTokenModel, UserModel, UserRole


JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALG = os.getenv("JWT_ALG", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))
REFRESH_TOKEN_COOKIE_NAME = os.getenv("REFRESH_TOKEN_COOKIE_NAME", "flowers_refresh_token")
REFRESH_TOKEN_COOKIE_SECURE = os.getenv("REFRESH_TOKEN_COOKIE_SECURE", "false").lower() == "true"
REFRESH_TOKEN_COOKIE_SAMESITE = os.getenv("REFRESH_TOKEN_COOKIE_SAMESITE", "lax")
REFRESH_TOKEN_COOKIE_PATH = "/auth"
USERNAME_MAX_LENGTH = 50
PASSWORD_MAX_LENGTH = 30

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
security = HTTPBearer(auto_error=False)
auth_router = APIRouter()


class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=USERNAME_MAX_LENGTH)
    password: str = Field(min_length=6, max_length=PASSWORD_MAX_LENGTH)


class UserLogin(BaseModel):
    username: str = Field(min_length=1, max_length=USERNAME_MAX_LENGTH)
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


class UserOut(BaseModel):
    id: int
    username: str
    role: UserRole


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _create_access_token(*, sub: str, role: str) -> str:
    now = _utcnow()
    payload = {
        "sub": sub,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def _hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        value=token,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=REFRESH_TOKEN_COOKIE_SECURE,
        samesite=REFRESH_TOKEN_COOKIE_SAMESITE,
        path=REFRESH_TOKEN_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        httponly=True,
        secure=REFRESH_TOKEN_COOKIE_SECURE,
        samesite=REFRESH_TOKEN_COOKIE_SAMESITE,
        path=REFRESH_TOKEN_COOKIE_PATH,
    )


def _create_refresh_token(db: Session, user: UserModel) -> str:
    raw_token = secrets.token_urlsafe(48)
    row = RefreshTokenModel(
        user_id=user.id,
        jti=secrets.token_urlsafe(32),
        token_hash=_hash_refresh_token(raw_token),
        expires_at=_utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(row)
    db.flush()
    return raw_token


def _issue_token_pair(response: Response, db: Session, user: UserModel) -> TokenOut:
    access_token = _create_access_token(sub=user.username, role=user.role.value)
    refresh_token = _create_refresh_token(db, user)
    db.commit()
    _set_refresh_cookie(response, refresh_token)
    return TokenOut(access_token=access_token)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> UserModel:
    if creds is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Не выполнен вход")

    token = creds.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный токен")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный токен")

    user = db.query(UserModel).filter(UserModel.username == username).one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь не найден")
    return user


def require_admin(user: UserModel = Depends(get_current_user)) -> UserModel:
    if user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ только для администратора")
    return user


@auth_router.post("/auth/register", response_model=UserOut, tags=["guest"])
def register(payload: UserRegister, db: Session = Depends(get_db)) -> UserOut:
    exists = db.query(UserModel).filter(UserModel.username == payload.username).one_or_none()
    if exists is not None:
        raise HTTPException(status_code=400, detail="Пользователь с таким логином уже существует")

    user = UserModel(
        username=payload.username,
        password_hash=pwd_context.hash(payload.password),
        role=UserRole.user,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut(id=user.id, username=user.username, role=user.role)


@auth_router.post("/auth/login", response_model=TokenOut, tags=["guest"])
def login(payload: UserLogin, response: Response, db: Session = Depends(get_db)) -> TokenOut:
    user = db.query(UserModel).filter(UserModel.username == payload.username).one_or_none()
    if user is None or not pwd_context.verify(payload.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Неверный логин или пароль")

    return _issue_token_pair(response, db, user)


@auth_router.post("/auth/refresh", response_model=TokenOut, tags=["guest"])
def refresh_access_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenOut:
    raw_refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)
    if not raw_refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Сессия не найдена")

    token_hash = _hash_refresh_token(raw_refresh_token)
    row = db.query(RefreshTokenModel).filter(RefreshTokenModel.token_hash == token_hash).one_or_none()
    now = _utcnow()
    expires_at = row.expires_at if row is not None else None
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if row is None or row.revoked_at is not None or expires_at is None or expires_at <= now:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Сессия истекла или недействительна")

    user = db.query(UserModel).filter(UserModel.id == row.user_id).one_or_none()
    if user is None:
        row.revoked_at = now
        db.commit()
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь не найден")

    new_raw_refresh_token = secrets.token_urlsafe(48)
    new_jti = secrets.token_urlsafe(32)
    row.revoked_at = now
    row.replaced_by_jti = new_jti
    db.add(
        RefreshTokenModel(
            user_id=user.id,
            jti=new_jti,
            token_hash=_hash_refresh_token(new_raw_refresh_token),
            expires_at=now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )
    access_token = _create_access_token(sub=user.username, role=user.role.value)
    db.commit()
    _set_refresh_cookie(response, new_raw_refresh_token)
    return TokenOut(access_token=access_token)


@auth_router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT, tags=["guest"])
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> Response:
    raw_refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)
    if raw_refresh_token:
        token_hash = _hash_refresh_token(raw_refresh_token)
        row = db.query(RefreshTokenModel).filter(RefreshTokenModel.token_hash == token_hash).one_or_none()
        if row is not None and row.revoked_at is None:
            row.revoked_at = _utcnow()
            db.commit()

    _clear_refresh_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@auth_router.get("/me", response_model=UserOut, tags=["user"])
def me(current_user: UserModel = Depends(get_current_user)) -> UserOut:
    return UserOut(id=current_user.id, username=current_user.username, role=current_user.role)
