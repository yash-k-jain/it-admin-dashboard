from datetime import datetime, timezone
from unittest.mock import patch

SYSTEM = "app.routes.system"

def test_get_settings(admin_client):
    settings = [
        {"key": "maintenance_mode", "value": False},
        {"key": "company_name", "value": "Mind Factry"},
        {"key": "max_login_attempts", "value": 5},
    ]
    with patch(f"{SYSTEM}.db") as db:
        db.system_settings.find.return_value = settings
        response = admin_client.get("/api/v1/system/settings")
        assert response.status_code == 200
        assert response.json() == {
            "maintenance_mode": False,
            "company_name": "Mind Factry",
            "max_login_attempts": 5,
        }

def test_update_setting(admin_client):
    with patch(f"{SYSTEM}.db") as db, \
         patch(f"{SYSTEM}.now", return_value=datetime.now(timezone.utc)), \
         patch(f"{SYSTEM}.audit") as audit:
        response = admin_client.put(
            "/api/v1/system/settings/maintenance_mode",
            json={"value": "True"}
        )
        assert response.status_code == 200
        assert response.json()["message"] == "System setting updated."
        db.system_settings.update_one.assert_called_once()
        audit.assert_called_once_with(
            "admin@example.com",
            "UPDATE_SYSTEM_SETTING",
            details={"key": "maintenance_mode"}
        )

def test_update_setting_key_too_long(admin_client):
    key = "x" * 101
    response = admin_client.put(
        f"/api/v1/system/settings/{key}",
        json={"value": "True"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid setting key."
