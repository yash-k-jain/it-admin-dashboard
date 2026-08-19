import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config.settings import settings

def now():
    return datetime.now(timezone.utc)

def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

def verify_password(password: str, hashed: bytes) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed)

def create_access_token(email: str, role: str):
    exp = now() + timedelta(minutes=settings.ACCESS_TOKEN_MINUTES)
    payload = {"sub": email, "email": email, "role": role, "type": "access", "exp": exp}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token():
    return secrets.token_urlsafe(48)

def create_one_time_token():
    return secrets.token_urlsafe(48)

def token_hash(token: str):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def decode_access_token(token: str):
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
