from fastapi import APIRouter, Depends, HTTPException

from app.config.database import db
from app.schemas.system import SystemSettingRequest
from app.utils.audit import audit
from app.utils.dependencies import require_admin
from app.utils.security import now

router = APIRouter(prefix="/api/v1/system", tags=["system"])

@router.get("/settings")
def get_settings(admin=Depends(require_admin)):
    settings = {}
    for item in db.system_settings.find():
        settings[item["key"]] = item["value"]
    return settings

@router.put("/settings/{key}")
def update_setting(key: str, payload: SystemSettingRequest, admin=Depends(require_admin)):
    if len(key) > 100:
        raise HTTPException(status_code=400, detail="Invalid setting key.")
    db.system_settings.update_one(
        {"key": key},
        {"$set": {"key": key, "value": payload.value, "updated_at": now()}},
        upsert=True,
    )
    audit(admin["email"], "UPDATE_SYSTEM_SETTING", details={"key": key})
    return {"message": "System setting updated."}
