from fastapi.testclient import TestClient

from app.main import app


def test_webhook_notification_is_listed() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/webhooks/google-calendar",
            headers={
                "x-goog-channel-id": "channel-test",
                "x-goog-resource-id": "resource-test",
                "x-goog-resource-state": "exists",
                "x-goog-message-number": "1",
            },
        )

        assert response.status_code == 202

        listed = client.get("/webhooks/google-calendar/notifications?limit=1")
        assert listed.status_code == 200
        body = listed.json()
        assert body
        assert body[-1]["channel_id"] == "channel-test"
        assert body[-1]["resource_state"] == "exists"
