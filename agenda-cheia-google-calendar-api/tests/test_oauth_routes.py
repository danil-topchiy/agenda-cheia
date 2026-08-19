from fastapi.testclient import TestClient

from app.main import app


def test_oauth_connections_route_is_available() -> None:
    with TestClient(app) as client:
        response = client.get("/auth/google/connections")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_oauth_login_requires_oauth_configuration() -> None:
    with TestClient(app) as client:
        response = client.get("/auth/google/login?user_id=test-user")

    assert response.status_code == 503
    assert "Google OAuth is not configured" in response.json()["detail"]
