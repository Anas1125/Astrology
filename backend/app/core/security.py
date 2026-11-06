from datetime import datetime, timedelta, timezone
import jwt
from pwdlib import PasswordHash
from app.core.config import settings

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def create_access_token(subject: str, auth_version: int = 0, expires_minutes: int = 20) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": subject, "ver": auth_version, "iat": now, "exp": now + timedelta(minutes=expires_minutes)}, settings.secret_key, algorithm="HS256")
