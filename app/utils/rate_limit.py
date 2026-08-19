from datetime import datetime, timedelta, timezone
from fastapi import HTTPException

from app.config.database import db
from app.config.settings import settings

def check_login_allowed(email: str):
    key = f"login:{email.lower()}"
    now = datetime.now(timezone.utc)
    doc = db.login_attempts.find_one({"key": key})
    if doc and doc["expires_at"] > now and doc.get("attempts", 0) >= settings.LOGIN_MAX_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")

def record_failed_login(email: str):
    key = f"login:{email.lower()}"
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=settings.LOGIN_WINDOW_MINUTES)
    db.login_attempts.update_one(
        {"key": key},
        {"$inc": {"attempts": 1}, "$set": {"expires_at": expires}},
        upsert=True,
    )

def clear_login_attempts(email: str):
    db.login_attempts.delete_one({"key": f"login:{email.lower()}"})
