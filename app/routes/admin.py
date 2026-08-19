from fastapi import APIRouter, Depends, HTTPException, Query
from bson import ObjectId

from app.config.database import db
from app.schemas.users import AdminUserUpdateRequest, AdminResetPasswordRequest
from app.utils.audit import audit
from app.utils.dependencies import require_admin
from app.utils.security import hash_password, now

router = APIRouter(prefix="/api/v1/admin", tags=["IT Admin"])

def serialize_user(user):
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "role": user["role"],
        "status": user.get("status", "active"),
        "name": user.get("name"),
        "phone": user.get("phone"),
        "created_at": user.get("created_at"),
        "updated_at": user.get("updated_at"),
    }

@router.get("/users")
def list_users(
    search: str | None = Query(default=None),
    status: str | None = Query(default=None),
    role: str | None = Query(default=None),
    skip: int = 0,
    limit: int = 50,
    admin=Depends(require_admin),
):
    query = {}
    if search:
        query["email"] = {"$regex": search, "$options": "i"}
    if status:
        query["status"] = status
    if role:
        query["role"] = role

    users = db.users.find(query).sort("created_at", -1).skip(skip).limit(min(limit, 100))
    return {"users": [serialize_user(u) for u in users]}

@router.get("/users/{user_id}")
def get_user(user_id: str, admin=Depends(require_admin)):
    try:
        user = db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID.")
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return serialize_user(user)

@router.patch("/users/{user_id}")
def update_user(user_id: str, payload: AdminUserUpdateRequest, admin=Depends(require_admin)):
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID.")

    user = db.users.find_one({"_id": oid})
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    updates = payload.model_dump(exclude_unset=True)
    if "role" in updates:
        updates["role"] = updates["role"].upper()
        if updates["role"] not in {"USER", "IT_ADMIN"}:
            raise HTTPException(status_code=400, detail="Invalid role.")
    if "status" in updates:
        if updates["status"] not in {"active", "inactive", "blocked"}:
            raise HTTPException(status_code=400, detail="Invalid status.")
        if user["email"] == admin["email"] and updates["status"] != "active":
            raise HTTPException(status_code=400, detail="You cannot deactivate your own account.")

    updates["updated_at"] = now()
    db.users.update_one({"_id": oid}, {"$set": updates})
    audit(admin["email"], "UPDATE_USER", user["email"], updates)
    return {"message": "User updated successfully."}

@router.post("/users/{user_id}/reset-password")
def admin_reset_password(user_id: str, payload: AdminResetPasswordRequest, admin=Depends(require_admin)):
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID.")
    user = db.users.find_one({"_id": oid})
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    db.users.update_one(
        {"_id": oid},
        {"$set": {"password": hash_password(payload.new_password), "updated_at": now()}},
    )
    db.refresh_tokens.update_many({"email": user["email"]}, {"$set": {"revoked": True}})
    audit(admin["email"], "ADMIN_RESET_PASSWORD", user["email"])
    return {"message": "Password reset successfully."}

@router.delete("/users/{user_id}")
def delete_user(user_id: str, admin=Depends(require_admin)):
    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID.")
    user = db.users.find_one({"_id": oid})
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if user["email"] == admin["email"]:
        raise HTTPException(status_code=400, detail="You cannot delete your own account.")

    db.users.delete_one({"_id": oid})
    db.refresh_tokens.delete_many({"email": user["email"]})
    audit(admin["email"], "DELETE_USER", user["email"])
    return {"message": "User deleted successfully."}

@router.get("/dashboard")
def dashboard(admin=Depends(require_admin)):
    total = db.users.count_documents({})
    active = db.users.count_documents({"status": "active"})
    inactive = db.users.count_documents({"status": "inactive"})
    blocked = db.users.count_documents({"status": "blocked"})
    users = db.users.count_documents({"role": "USER"})
    admins = db.users.count_documents({"role": "IT_ADMIN"})
    recent_audit = list(db.audit_logs.find().sort("created_at", -1).limit(10))

    for item in recent_audit:
        item["_id"] = str(item["_id"])

    return {
        "users": {"total": total, "active": active, "inactive": inactive, "blocked": blocked},
        "roles": {"USER": users, "IT_ADMIN": admins},
        "recent_audit_logs": recent_audit,
    }

@router.get("/audit-logs")
def audit_logs(
    skip: int = 0,
    limit: int = 50,
    admin=Depends(require_admin),
):
    logs = db.audit_logs.find().sort("created_at", -1).skip(skip).limit(min(limit, 100))
    result = []
    for log in logs:
        log["_id"] = str(log["_id"])
        result.append(log)
    return {"logs": result}
