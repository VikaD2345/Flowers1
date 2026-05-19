import sys
import unittest
from pathlib import Path

from jose import jwt
from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from auth import JWT_ALG, JWT_SECRET, UserLogin, UserRegister, _create_access_token, _hash_refresh_token, require_admin
from models import UserRole


class FakeUser:
    def __init__(self, role):
        self.role = role


class AuthUnitTests(unittest.TestCase):
    def test_hash_refresh_token_is_deterministic(self):
        hashed_once = _hash_refresh_token("refresh-token")
        hashed_twice = _hash_refresh_token("refresh-token")

        self.assertEqual(hashed_once, hashed_twice)
        self.assertEqual(len(hashed_once), 64)

    def test_create_access_token_contains_subject_and_role(self):
        token = _create_access_token(sub="alice", role="admin")
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])

        self.assertEqual(payload["sub"], "alice")
        self.assertEqual(payload["role"], "admin")
        self.assertGreater(payload["exp"], payload["iat"])

    def test_require_admin_returns_admin_user(self):
        admin_user = FakeUser(UserRole.admin)

        self.assertIs(require_admin(admin_user), admin_user)

    def test_require_admin_rejects_non_admin_user(self):
        with self.assertRaises(Exception) as context:
            require_admin(FakeUser(UserRole.user))

        self.assertEqual(context.exception.status_code, 403)

    def test_user_models_validate_credentials_length(self):
        valid = UserLogin(username="anna", password="secret1")
        self.assertEqual(valid.username, "anna")

        with self.assertRaises(ValidationError):
            UserRegister(username="ab", password="123")


AuthUnitTests.test_hash_refresh_token_is_deterministic.__doc__ = "детерминированно хеширует refresh token"
AuthUnitTests.test_create_access_token_contains_subject_and_role.__doc__ = "создаёт access token с полями sub и role"
AuthUnitTests.test_require_admin_returns_admin_user.__doc__ = "разрешает доступ пользователю с ролью администратора"
AuthUnitTests.test_require_admin_rejects_non_admin_user.__doc__ = "запрещает доступ пользователю без роли администратора"
AuthUnitTests.test_user_models_validate_credentials_length.__doc__ = "валидирует длину логина и пароля в pydantic-моделях"


if __name__ == "__main__":
    unittest.main()
