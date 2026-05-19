import sys
import unittest
from http.cookies import SimpleCookie
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request
from starlette.responses import Response

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from auth import (
    REFRESH_TOKEN_COOKIE_NAME,
    UserLogin,
    UserRegister,
    login,
    logout,
    refresh_access_token,
    register,
)
from database import Base
from models import RefreshTokenModel, UserModel, UserRole


def make_request(cookie_value=None):
    headers = []
    if cookie_value:
      headers.append((b"cookie", f"{REFRESH_TOKEN_COOKIE_NAME}={cookie_value}".encode("utf-8")))
    return Request({"type": "http", "method": "POST", "path": "/", "headers": headers})


def get_cookie_value(response):
    cookie = SimpleCookie()
    cookie.load(response.headers.get("set-cookie", ""))
    morsel = cookie.get(REFRESH_TOKEN_COOKIE_NAME)
    return morsel.value if morsel else None


class AuthAutoTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", future=True)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.Session()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_register_creates_regular_user(self):
        result = register(UserRegister(username="mila", password="secret1"), db=self.db)

        self.assertEqual(result.username, "mila")
        self.assertEqual(result.role, UserRole.user)
        self.assertIsNotNone(self.db.query(UserModel).filter_by(username="mila").one_or_none())

    def test_register_rejects_duplicate_username(self):
        register(UserRegister(username="mila", password="secret1"), db=self.db)

        with self.assertRaises(HTTPException) as context:
            register(UserRegister(username="mila", password="secret1"), db=self.db)

        self.assertEqual(context.exception.status_code, 400)

    def test_login_returns_access_token_and_sets_refresh_cookie(self):
        register(UserRegister(username="mila", password="secret1"), db=self.db)
        response = Response()

        result = login(UserLogin(username="mila", password="secret1"), response=response, db=self.db)

        self.assertTrue(result.access_token)
        self.assertEqual(result.token_type, "bearer")
        self.assertIsNotNone(get_cookie_value(response))

    def test_refresh_requires_cookie(self):
        with self.assertRaises(HTTPException) as context:
            refresh_access_token(make_request(), Response(), db=self.db)

        self.assertEqual(context.exception.status_code, 401)

    def test_logout_revokes_refresh_token(self):
        register(UserRegister(username="mila", password="secret1"), db=self.db)
        login_response = Response()
        login(UserLogin(username="mila", password="secret1"), response=login_response, db=self.db)
        refresh_token = get_cookie_value(login_response)

        response = Response()
        logout(make_request(refresh_token), response=response, db=self.db)

        token_row = self.db.query(RefreshTokenModel).one()
        self.assertIsNotNone(token_row.revoked_at)


AuthAutoTests.test_register_creates_regular_user.__doc__ = "регистрирует обычного пользователя"
AuthAutoTests.test_register_rejects_duplicate_username.__doc__ = "не позволяет зарегистрировать пользователя с уже существующим логином"
AuthAutoTests.test_login_returns_access_token_and_sets_refresh_cookie.__doc__ = "возвращает access token и выставляет refresh cookie при входе"
AuthAutoTests.test_refresh_requires_cookie.__doc__ = "не выполняет refresh без cookie"
AuthAutoTests.test_logout_revokes_refresh_token.__doc__ = "отзывает refresh token при выходе из системы"


if __name__ == "__main__":
    unittest.main()
