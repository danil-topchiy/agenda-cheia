import os
import time

import httpx
import pytest


def test_create_and_pay_woovi_sandbox_charge():
    app_id = os.environ.get("WOOVI_SANDBOX_APP_ID")
    if not app_id:
        pytest.skip("WOOVI_SANDBOX_APP_ID nao configurado")

    base_url = os.environ.get(
        "WOOVI_SANDBOX_API_BASE_URL", "https://api.woovi-sandbox.com"
    ).rstrip("/")
    correlation_id = f"agenda-sandbox-{int(time.time())}"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": app_id,
    }

    with httpx.Client(timeout=30.0, follow_redirects=False) as client:
        created = client.post(
            f"{base_url}/api/v1/charge",
            headers=headers,
            json={
                "value": 1,
                "correlationID": correlation_id,
                "comment": "Teste sandbox Agenda Cheia",
            },
        )

        assert created.status_code == 200, created.text
        created_body = created.json()
        charge = created_body["charge"]
        assert charge["correlationID"] == correlation_id
        assert charge["status"] == "ACTIVE"

        paid = client.get(
            f"{base_url}/openpix/testing",
            headers={"Accept": "application/json", "Authorization": app_id},
            params={"transactionID": charge["transactionID"]},
        )

        assert paid.status_code in {200, 302}, paid.text

        retrieved = client.get(
            f"{base_url}/api/v1/charge/{correlation_id}",
            headers={"Accept": "application/json", "Authorization": app_id},
        )

        assert retrieved.status_code == 200, retrieved.text
        retrieved_charge = retrieved.json()["charge"]
        assert retrieved_charge["status"] == "COMPLETED"
        assert retrieved_charge["paidAt"]
