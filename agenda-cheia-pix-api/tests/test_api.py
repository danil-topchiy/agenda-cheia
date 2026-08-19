from typing import Any
from contextlib import contextmanager

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


class FakeWooviClient:
    def __init__(self) -> None:
        self.payload: dict[str, Any] | None = None
        self.webhook_payload: dict[str, Any] | None = None

    async def create_charge(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.payload = payload
        return {
            "charge": {
                "value": payload["value"],
                "identifier": "provider-123",
                "correlationID": payload["correlationID"],
                "paymentLinkID": "payment-link-123",
                "transactionID": "provider-123",
                "status": "ACTIVE",
                "expiresIn": payload["expiresIn"],
                "expiresDate": "2026-08-19T15:00:00.000Z",
                "brCode": "000201...",
                "qrCodeImage": "https://api.woovi.com/woovi/charge/brcode/image/payment-link-123.png",
                "paymentLinkUrl": "https://woovi.com/pay/payment-link-123",
            },
            "correlationID": payload["correlationID"],
            "brCode": "000201...",
        }

    async def create_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.webhook_payload = payload
        webhook = {
            "id": "webhook-123",
            "name": payload["webhook"]["name"],
            "event": payload["webhook"]["event"],
            "url": payload["webhook"]["url"],
            "authorization": payload["webhook"].get("authorization"),
            "isActive": payload["webhook"]["isActive"],
        }
        return {"webhook": webhook}


@contextmanager
def make_client(tmp_path, **overrides):
    settings = Settings(
        WOOVI_APP_ID="test-app-id",
        DATABASE_PATH=str(tmp_path / "test.db"),
        WOOVI_WEBHOOK_VERIFY_SIGNATURE=False,
        **overrides,
    )
    app = create_app(settings)

    with TestClient(app) as client:
        fake_woovi = FakeWooviClient()
        app.state.woovi_client = fake_woovi
        yield client, fake_woovi


def test_create_charge_sends_expiration_and_persists_record(tmp_path):
    with make_client(tmp_path) as (client, fake_woovi):
        response = client.post(
            "/charges",
            json={
                "value": 1500,
                "expiresIn": 900,
                "correlationID": "agenda-123",
                "comment": "Agendamento agenda-123",
            },
        )

        assert response.status_code == 201
        body = response.json()
        assert body["correlationID"] == "agenda-123"
        assert body["status"] == "ACTIVE"
        assert body["expiresIn"] == 900
        assert body["brCode"] == "000201..."
        assert fake_woovi.payload["expiresIn"] == 900

        stored = client.get("/charges/agenda-123")
        assert stored.status_code == 200
        assert stored.json()["status"] == "ACTIVE"


def test_charge_flow_updates_created_charge_after_payment_webhook(tmp_path):
    correlation_id = "agenda-flow-001"

    with make_client(tmp_path) as (client, fake_woovi):
        created = client.post(
            "/charges",
            json={
                "value": 500,
                "expiresIn": 600,
                "correlationID": correlation_id,
                "comment": "Sinal do agendamento agenda-flow-001",
                "customer": {
                    "name": "Cliente Teste",
                    "email": "cliente@example.com",
                    "phone": "5511999999999",
                },
            },
        )

        assert created.status_code == 201
        assert created.json()["status"] == "ACTIVE"
        assert fake_woovi.payload == {
            "value": 500,
            "expiresIn": 600,
            "correlationID": correlation_id,
            "comment": "Sinal do agendamento agenda-flow-001",
            "customer": {
                "name": "Cliente Teste",
                "email": "cliente@example.com",
                "phone": "5511999999999",
            },
        }

        paid = client.post(
            "/webhooks/woovi",
            json={
                "event": "OPENPIX:CHARGE_COMPLETED",
                "charge": {
                    "value": 500,
                    "identifier": "provider-123",
                    "transactionID": "provider-123",
                    "correlationID": correlation_id,
                    "paymentLinkID": "payment-link-123",
                    "status": "COMPLETED",
                    "paidAt": "2026-08-19T15:10:00.000Z",
                },
                "pix": {
                    "charge": {
                        "value": 500,
                        "identifier": "provider-123",
                        "transactionID": "provider-123",
                        "correlationID": correlation_id,
                        "paymentLinkID": "payment-link-123",
                        "status": "COMPLETED",
                        "paidAt": "2026-08-19T15:10:00.000Z",
                    },
                    "value": 500,
                    "status": "CONFIRMED",
                    "transactionID": "provider-123",
                },
            },
        )

        assert paid.status_code == 200

        stored = client.get(f"/charges/{correlation_id}")
        assert stored.status_code == 200
        body = stored.json()
        assert body["status"] == "COMPLETED"
        assert body["paidAt"] == "2026-08-19T15:10:00.000Z"
        assert body["providerChargeID"] == "provider-123"
        assert body["paymentLinkID"] == "payment-link-123"
        assert body["brCode"] == "000201..."
        assert body["paymentLinkUrl"] == "https://woovi.com/pay/payment-link-123"


def test_webhook_completed_updates_charge_status(tmp_path):
    with make_client(tmp_path) as (client, _):
        response = client.post(
            "/webhooks/woovi",
            json={
                "event": "OPENPIX:CHARGE_COMPLETED",
                "charge": {
                    "value": 1500,
                    "correlationID": "agenda-456",
                    "status": "COMPLETED",
                    "paidAt": "2026-08-19T15:05:00.000Z",
                },
            },
        )

        assert response.status_code == 200
        assert response.content == b""

        stored = client.get("/charges/agenda-456")
        assert stored.status_code == 200
        body = stored.json()
        assert body["status"] == "COMPLETED"
        assert body["paidAt"] == "2026-08-19T15:05:00.000Z"


def test_webhook_authorization_is_checked_when_configured(tmp_path):
    settings = Settings(
        WOOVI_APP_ID="test-app-id",
        DATABASE_PATH=str(tmp_path / "test.db"),
        WOOVI_WEBHOOK_VERIFY_SIGNATURE=False,
        WOOVI_WEBHOOK_AUTHORIZATION="secret",
    )
    app = create_app(settings)

    with TestClient(app) as client:
        denied = client.post(
            "/webhooks/woovi",
            json={"event": "OPENPIX:CHARGE_COMPLETED"},
        )
        assert denied.status_code == 401

        accepted = client.post(
            "/webhooks/woovi",
            headers={"Authorization": "secret"},
            json={"event": "OPENPIX:CHARGE_COMPLETED"},
        )
        assert accepted.status_code == 200


def test_create_webhook_registers_url_in_woovi(tmp_path):
    with make_client(
        tmp_path,
        WOOVI_WEBHOOK_AUTHORIZATION="shared-secret",
    ) as (client, fake_woovi):
        response = client.post(
            "/webhooks",
            json={
                "name": "agenda-cheia-dev-completed",
                "event": "OPENPIX:CHARGE_COMPLETED",
                "url": "https://example.com/webhooks/woovi",
            },
        )

        assert response.status_code == 201
        assert fake_woovi.webhook_payload == {
            "webhook": {
                "name": "agenda-cheia-dev-completed",
                "event": "OPENPIX:CHARGE_COMPLETED",
                "url": "https://example.com/webhooks/woovi",
                "isActive": True,
                "authorization": "shared-secret",
            }
        }

        body = response.json()
        assert body["id"] == "webhook-123"
        assert body["name"] == "agenda-cheia-dev-completed"
        assert body["event"] == "OPENPIX:CHARGE_COMPLETED"
        assert body["url"] == "https://example.com/webhooks/woovi"
        assert body["isActive"] is True
        assert body["raw"]["webhook"]["authorization"] == "********"
