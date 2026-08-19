from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Response
from pymongo.errors import DuplicateKeyError

from app.config.database import db
from app.config.settings import settings
from app.schemas.auth import (
    RegisterRequest, LoginRequest, ForgotPasswordRequest, ResetPasswordRequest,
    ChangePasswordRequest, RefreshRequest,
)
from app.utils.audit import audit
from app.utils.dependencies import get_current_user
from app.utils.email import send_password_reset_email
from app.utils.rate_limit import check_login_allowed, record_failed_login, clear_login_attempts
from app.utils.security import (
    hash_password, verify_password, create_access_token, create_refresh_token,
    create_one_time_token, token_hash, now,
)
from datetime import datetime

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])

def set_access_cookie(response: Response, token: str):
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.ACCESS_TOKEN_MINUTES * 60,
    )

def store_refresh_token(email: str, token: str):
    db.refresh_tokens.insert_one({
        "email": email,
        "token_hash": token_hash(token),
        "created_at": now(),
        "expires_at": now() + timedelta(days=settings.REFRESH_TOKEN_DAYS),
        "revoked": False,
    })

@router.post("/register")
def register_user(response: Response, payload: RegisterRequest):
    existing = db.users.find_one({"email": payload.email.lower()})
    if existing:
        raise HTTPException(status_code=409, detail="User already exists.")

    # Public registration cannot create an IT Admin.
    role = "USER"
    user = {
        "email": payload.email.lower(),
        "password": hash_password(payload.password),
        "role": role,
        "status": "active",
        "name": None,
        "phone": None,
        "created_at": now(),
        "updated_at": now(),
    }
    try:
        db.users.insert_one(user)
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="User already exists.")

    access = create_access_token(user["email"], role)
    refresh = create_refresh_token()
    store_refresh_token(user["email"], refresh)
    set_access_cookie(response, access)
    audit(user["email"], "REGISTER")
    return {"message": "User registered successfully!", "refresh_token": refresh}

@router.post("/login")
def login_user(response: Response, payload: LoginRequest):
    email = payload.email.lower()
    check_login_allowed(email)
    user = db.users.find_one({"email": email})

    if not user or not verify_password(payload.password, user["password"]):
        record_failed_login(email)
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    if user.get("status") != "active":
        raise HTTPException(status_code=403, detail="User account is not active.")

    clear_login_attempts(email)
    access = create_access_token(user["email"], user["role"])
    refresh = create_refresh_token()
    store_refresh_token(user["email"], refresh)
    set_access_cookie(response, access)
    audit(email, "LOGIN")
    return {"message": "Login successful!", "refresh_token": refresh}

@router.post("/refresh")
def refresh_token(response: Response, payload: RefreshRequest):
    if not payload.refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token is required.")

    stored = db.refresh_tokens.find_one({
        "token_hash": token_hash(payload.refresh_token),
        "revoked": False,
        "expires_at": {"$gt": now()},
    })
    if not stored:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token.")
    
    db.refresh_tokens.update_one({"_id": stored["_id"]}, {"$set": {"revoked": True}})
    user = db.users.find_one({"email": stored["email"]})
    if not user or user.get("status") != "active":
        raise HTTPException(status_code=403, detail="User account is not active.")

    access = create_access_token(user["email"], user["role"])
    new_refresh = create_refresh_token()
    store_refresh_token(user["email"], new_refresh)
    set_access_cookie(response, access)
    return {"message": "Token refreshed.", "refresh_token": new_refresh}

@router.get("/me")
def get_current_user_profile(user=Depends(get_current_user)):
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "role": user["role"],
        "status": user["status"],
        "name": user.get("name"),
        "phone": user.get("phone"),
    }

@router.post("/change-password")
def change_password(payload: ChangePasswordRequest, user=Depends(get_current_user)):
    if not verify_password(payload.current_password, user["password"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=400, detail="New password must be different.")

    db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"password": hash_password(payload.new_password), "updated_at": now()}},
    )
    db.refresh_tokens.update_many({"email": user["email"]}, {"$set": {"revoked": True}})
    audit(user["email"], "CHANGE_PASSWORD")
    return {"message": "Password changed successfully."}

@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest):
    # Same response whether or not the account exists to avoid account enumeration.
    user = db.users.find_one({"email": payload.email.lower()})
    if user:
        token = create_one_time_token()
        db.password_reset_tokens.insert_one({
            "email": user["email"],
            "token_hash": token_hash(token),
            "created_at": now(),
            "expires_at": now() + timedelta(minutes=settings.RESET_TOKEN_MINUTES),
            "used": False,
        })
        reset_url = f"{settings.FRONTEND_RESET_URL}?token={token}"
        send_password_reset_email(user["email"], reset_url)
        audit(user["email"], "PASSWORD_RESET_REQUEST")
    return {"message": "If the email exists, a password reset link has been sent."}

@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest):
    record = db.password_reset_tokens.find_one({
        "token_hash": token_hash(payload.token),
        "used": False,
        "expires_at": {"$gt": now()},
    })
    if not record:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")

    db.users.update_one(
        {"email": record["email"]},
        {"$set": {"password": hash_password(payload.new_password), "updated_at": now()}},
    )
    db.password_reset_tokens.update_one({"_id": record["_id"]}, {"$set": {"used": True}})
    db.refresh_tokens.update_many({"email": record["email"]}, {"$set": {"revoked": True}})
    audit(record["email"], "PASSWORD_RESET")
    return {"message": "Password reset successfully."}

@router.post("/logout")
def logout_user(response: Response, user=Depends(get_current_user)):
    db.refresh_tokens.update_many({"email": user["email"]}, {"$set": {"revoked": True}})
    response.delete_cookie("access_token")
    audit(user["email"], "LOGOUT")
    return {"message": "Logout successful!"}
