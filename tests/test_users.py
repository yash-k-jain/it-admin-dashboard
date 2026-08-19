from unittest.mock import patch

USERS = "app.routes.admin"

def test_get_user_invalid_id(admin_client):
    with patch(f"{USERS}.ObjectId", side_effect=Exception()):
        response = admin_client.get("/api/v1/admin/users/not-valid")
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid user ID."

def test_get_user_not_found(admin_client):
    with patch(f"{USERS}.ObjectId", return_value="oid"), \
         patch(f"{USERS}.db") as db:
        db.users.find_one.return_value = None
        response = admin_client.get("/api/v1/admin/users/507f1f77bcf86cd799439011")
        assert response.status_code == 404
        assert response.json()["detail"] == "User not found."

def test_get_user_success(admin_client):
    user = {"_id": "oid", "email": "user@example.com", "role": "USER", "status": "active"}
    with patch(f"{USERS}.ObjectId", return_value="oid"), \
         patch(f"{USERS}.db") as db, \
         patch(f"{USERS}.serialize_user", return_value={
             "id": "oid", "email": "user@example.com",
             "role": "USER", "status": "active"
         }):
        db.users.find_one.return_value = user
        response = admin_client.get("/api/v1/admin/users/507f1f77bcf86cd799439011")
        assert response.status_code == 200
        assert response.json()["email"] == "user@example.com"
