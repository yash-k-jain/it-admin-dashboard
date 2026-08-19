from datetime import datetime, timezone
from app.config.database import db

def audit(actor_email: str, action: str, target_email: str | None = None, details: dict | None = None):
    db.audit_logs.insert_one({
        "actor_email": actor_email,
        "action": action,
        "target_email": target_email,
        "details": details or {},
        "created_at": datetime.now(timezone.utc),
    })
