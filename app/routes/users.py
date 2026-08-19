from fastapi import APIRouter, Depends

from app.config.database import db
from app.schemas.users import ProfileUpdateRequest
from app.utils.audit import audit
from app.utils.dependencies import get_current_user
from app.utils.security import now

from bson import ObjectId

router = APIRouter(prefix="/api/v1/users", tags=["users"])

@router.get("/profile")
def get_profile(user=Depends(get_current_user)):
    return {
        "email": user["email"],
        "role": user["role"],
        "status": user["status"],
        "name": user.get("name"),
        "phone": user.get("phone"),
    }

@router.patch("/profile")
def update_profile(payload: ProfileUpdateRequest, user=Depends(get_current_user)):
    updates = payload.model_dump(exclude_unset=True)
    updates["updated_at"] = now()
    db.users.update_one({"_id": user["_id"]}, {"$set": updates})
    audit(user["email"], "UPDATE_PROFILE", user["email"], updates)
    return {"message": "Profile updated successfully."}
