import pytest
from fastapi.testclient import TestClient
from app.main import app

try:
    from app.utils.dependencies import get_current_user, require_admin
except ImportError:
    get_current_user = None
    require_admin = None

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def authenticated_user():
    return {
        "_id": "test-user-id",
        "email": "user@example.com",
        "password": "old-hash",
        "role": "USER",
        "status": "active",
    }

@pytest.fixture
def admin_user():
    return {
        "_id": "test-admin-id",
        "email": "admin@example.com",
        "password": "admin-hash",
        "role": "IT_ADMIN",
        "status": "active",
    }

@pytest.fixture
def authenticated_client(authenticated_user):
    if get_current_user is None:
        pytest.skip("Could not import get_current_user")
    app.dependency_overrides[get_current_user] = lambda: authenticated_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def admin_client(admin_user):
    if require_admin is None:
        pytest.skip("Could not import require_admin")
    app.dependency_overrides[require_admin] = lambda: admin_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
