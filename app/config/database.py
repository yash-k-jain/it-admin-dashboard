from pymongo import MongoClient, ASCENDING, DESCENDING
from app.config.settings import settings
from datetime import timezone

client = MongoClient(settings.DB_URI, serverSelectionTimeoutMS=5000, tz_aware=True)
db = client[settings.DB_NAME]


def ensure_indexes():
    db.users.create_index([("email", ASCENDING)], unique=True)
    db.refresh_tokens.create_index([("token_hash", ASCENDING)], unique=True)
    db.refresh_tokens.create_index([("expires_at", ASCENDING)], expireAfterSeconds=0)
    db.password_reset_tokens.create_index([("token_hash", ASCENDING)], unique=True)
    db.password_reset_tokens.create_index(
        [("expires_at", ASCENDING)], expireAfterSeconds=0
    )
    db.audit_logs.create_index([("created_at", DESCENDING)])
    db.login_attempts.create_index([("key", ASCENDING)], unique=True)
    db.login_attempts.create_index([("expires_at", ASCENDING)], expireAfterSeconds=0)
    db.system_settings.create_index([("key", ASCENDING)], unique=True)


try:
    client.admin.command("ping")
    print("Connected to MongoDB!")
except Exception as exc:
    print(f"MongoDB connection warning: {exc}")
