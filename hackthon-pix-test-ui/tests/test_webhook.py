import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import Settings
from app.webhook import simulated_webhook_payload, summarize_payload


def make_client():
    settings = Settings(
        PIX_API_BASE_URL="http://pix-api.test",
        PUBLIC_BASE_URL="http://ui.test",
        FORWARD_WEBHOOK_TO_PIX_API=False,
    )
    return TestClient(create_app(settings))


def test_simulated_completed_payload_is_summarized():
    payload = simulated_webhook_payload(
        correlation_id="agenda-1",
        value=500,
        status="COMPLETED",
        provider_charge_id="provider-1",
        payment_link_id="payment-1",
    )

    summary = summarize_payload(payload)

    assert payload["event"] == "OPENPIX:CHARGE_COMPLETED"
    assert summary["correlationID"] == "agenda-1"
    assert summary["status"] == "COMPLETED"
    assert summary["value"] == 500
    assert summary["paidAt"]


def test_webhook_endpoint_records_payload():
    with make_client() as client:
        response = client.post(
            "/webhooks/woovi",
            json={
                "event": "OPENPIX:CHARGE_EXPIRED",
                "charge": {
                    "correlationID": "agenda-2",
                    "value": 1000,
                    "status": "EXPIRED",
                },
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["summary"]["correlationID"] == "agenda-2"
        assert body["summary"]["status"] == "EXPIRED"

        events = client.get("/api/webhook-events").json()
        assert len(events) == 1
        assert events[0]["summary"]["event"] == "OPENPIX:CHARGE_EXPIRED"


def test_config_exposes_webhook_url():
    with make_client() as client:
        response = client.get("/api/config")

        assert response.status_code == 200
        assert response.json()["webhookUrl"] == "http://ui.test/webhooks/woovi"

