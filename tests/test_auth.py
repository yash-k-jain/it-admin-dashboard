from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

AUTH = "app.routes.auth"

def test_register_success(client):
    with patch(f"{AUTH}.db") as db, \
         patch(f"{AUTH}.hash_password", return_value="HASHED"), \
         patch(f"{AUTH}.create_access_token", return_value="ACCESS"), \
         patch(f"{AUTH}.create_refresh_token", return_value="REFRESH"), \
         patch(f"{AUTH}.store_refresh_token"), \
         patch(f"{AUTH}.set_access_cookie"), \
         patch(f"{AUTH}.audit"):
        db.users.find_one.return_value = None
        db.users.insert_one.return_value = MagicMock()
        response = client.post("/api/v1/auth/register", json={
            "email": "TEST@example.com", "password": "Password123!"
        })
        assert response.status_code in (200, 201)
        assert response.json()["message"] == "User registered successfully!"
        inserted = db.users.insert_one.call_args.args[0]
        assert inserted["email"] == "test@example.com"
        assert inserted["role"] == "USER"

def test_register_existing_user(client):
    with patch(f"{AUTH}.db") as db:
        db.users.find_one.return_value = {"email": "test@example.com"}
        response = client.post("/api/v1/auth/register", json={
            "email": "test@example.com", "password": "Password123!"
        })
        assert response.status_code == 409
        assert response.json()["detail"] == "User already exists."

def test_login_success(client):
    user = {
        "_id": "123", "email": "test@example.com", "password": "HASHED",
        "role": "USER", "status": "active"
    }
    with patch(f"{AUTH}.check_login_allowed") as allowed, \
         patch(f"{AUTH}.db") as db, \
         patch(f"{AUTH}.verify_password", return_value=True), \
         patch(f"{AUTH}.create_access_token", return_value="ACCESS"), \
         patch(f"{AUTH}.create_refresh_token", return_value="REFRESH"), \
         patch(f"{AUTH}.store_refresh_token") as store, \
         patch(f"{AUTH}.set_access_cookie") as cookie, \
         patch(f"{AUTH}.audit") as audit:
        db.users.find_one.return_value = user
        response = client.post("/api/v1/auth/login", json={
            "email": "TEST@example.com", "password": "Password123!"
        })
        assert response.status_code == 200
        assert response.json() == {
            "message": "Login successful!", "refresh_token": "REFRESH"
        }
        allowed.assert_called_once_with("test@example.com")
        store.assert_called_once()
        cookie.assert_called_once()
        audit.assert_called_once_with("test@example.com", "LOGIN")

def test_login_user_not_found(client):
    with patch(f"{AUTH}.check_login_allowed"), \
         patch(f"{AUTH}.db") as db, \
         patch(f"{AUTH}.record_failed_login") as failed:
        db.users.find_one.return_value = None
        response = client.post("/api/v1/auth/login", json={
            "email": "missing@example.com", "password": "Password123!"
        })
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password."
        failed.assert_called_once_with("missing@example.com")

def test_login_invalid_password(client):
    user = {
        "email": "test@example.com", "password": "HASHED",
        "role": "USER", "status": "active"
    }
    with patch(f"{AUTH}.check_login_allowed"), \
         patch(f"{AUTH}.db") as db, \
         patch(f"{AUTH}.verify_password", return_value=False), \
         patch(f"{AUTH}.record_failed_login") as failed:
        db.users.find_one.return_value = user
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com", "password": "Wrong!"
        })
        assert response.status_code == 401
        failed.assert_called_once_with("test@example.com")

def test_login_inactive_user(client):
    user = {
        "email": "test@example.com", "password": "HASHED",
        "role": "USER", "status": "inactive"
    }
    with patch(f"{AUTH}.check_login_allowed"), \
         patch(f"{AUTH}.db") as db, \
         patch(f"{AUTH}.verify_password", return_value=True):
        db.users.find_one.return_value = user
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com", "password": "Password123!"
        })
        assert response.status_code == 403
        assert response.json()["detail"] == "User account is not active."

def test_refresh_success(client):
    stored = {
        "_id": "refresh-id", "email": "test@example.com", "revoked": False,
        "expires_at": datetime.now(timezone.utc) + timedelta(days=1)
    }
    user = {"email": "test@example.com", "role": "USER", "status": "active"}
    with patch(f"{AUTH}.db") as db, \
         patch(f"{AUTH}.token_hash", return_value="HASHED"), \
         patch(f"{AUTH}.now", return_value=datetime.now(timezone.utc)), \
         patch(f"{AUTH}.create_access_token", return_value="NEW_ACCESS"), \
         patch(f"{AUTH}.create_refresh_token", return_value="NEW_REFRESH"), \
         patch(f"{AUTH}.store_refresh_token") as store, \
         patch(f"{AUTH}.set_access_cookie") as cookie:
        db.refresh_tokens.find_one.return_value = stored
        db.users.find_one.return_value = user
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": "OLD_REFRESH"
        })
        assert response.status_code == 200
        assert response.json()["refresh_token"] == "NEW_REFRESH"
        db.refresh_tokens.update_one.assert_called_once()
        store.assert_called_once()
        cookie.assert_called_once()

def test_refresh_invalid_or_expired(client):
    with patch(f"{AUTH}.db") as db:
        db.refresh_tokens.find_one.return_value = None
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": "BAD"
        })
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid or expired refresh token."

def test_refresh_missing(client):
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": ""})
    assert response.status_code == 401
    assert response.json()["detail"] == "Refresh token is required."

def test_refresh_inactive_user(client):
    stored = {
        "_id": "refresh-id", "email": "test@example.com", "revoked": False,
        "expires_at": datetime.now(timezone.utc) + timedelta(days=1)
    }
    with patch(f"{AUTH}.db") as db:
        db.refresh_tokens.find_one.return_value = stored
        db.users.find_one.return_value = {
            "email": "test@example.com", "role": "USER", "status": "inactive"
        }
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": "VALID"
        })
        assert response.status_code == 403
        assert response.json()["detail"] == "User account is not active."

def test_change_password_success(authenticated_client):
    with patch(f"{AUTH}.verify_password", return_value=True), \
         patch(f"{AUTH}.hash_password", return_value="NEW_HASH"), \
         patch(f"{AUTH}.now", return_value=datetime.now(timezone.utc)), \
         patch(f"{AUTH}.db") as db, \
         patch(f"{AUTH}.audit") as audit:
        response = authenticated_client.post("/api/v1/auth/change-password", json={
            "current_password": "OldPassword123!",
            "new_password": "NewPassword123!"
        })
        assert response.status_code == 200
        assert db.users.update_one.called
        db.refresh_tokens.update_many.assert_called_once_with(
            {"email": "user@example.com"}, {"$set": {"revoked": True}}
        )
        audit.assert_called_once_with("user@example.com", "CHANGE_PASSWORD")

def test_change_password_wrong_current_password(authenticated_client):
    with patch(f"{AUTH}.verify_password", return_value=False):
        response = authenticated_client.post("/api/v1/auth/change-password", json={
            "current_password": "Wrong!", "new_password": "NewPassword123!"
        })
        assert response.status_code == 400
        assert response.json()["detail"] == "Current password is incorrect."

def test_change_password_same_password(authenticated_client):
    with patch("app.routes.auth.verify_password", return_value=True):
        response = authenticated_client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "SamePassword123!",
                "new_password": "SamePassword123!"
            }
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "New password must be different."
