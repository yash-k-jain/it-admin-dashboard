import jwt
from fastapi import Cookie, Depends, HTTPException, status

from app.config.database import db
from app.config.settings import settings
from app.utils.security import decode_access_token

def get_current_payload(access_token: str | None = Cookie(default=None)):
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated. Cookie missing.")
    try:
        payload = decode_access_token(access_token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid access token.")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token.")

def get_current_user(payload: dict = Depends(get_current_payload)):
    email = payload.get("email")
    user = db.users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if user.get("status") != "active":
        raise HTTPException(status_code=403, detail="User account is not active.")
    return user

def require_admin(user=Depends(get_current_user)):
    if user.get("role") != "IT_ADMIN":
        raise HTTPException(status_code=403, detail="IT Admin access required.")
    return user
