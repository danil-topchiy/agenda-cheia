from datetime import UTC, datetime
from typing import Any


def extract_charge(payload: dict[str, Any]) -> dict[str, Any]:
    charge = payload.get("charge")
    if isinstance(charge, dict):
        return charge

    pix = payload.get("pix")
    if isinstance(pix, dict) and isinstance(pix.get("charge"), dict):
        return pix["charge"]

    return {}


def summarize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    charge = extract_charge(payload)
    return {
        "event": payload.get("event"),
        "correlationID": charge.get("correlationID"),
        "status": charge.get("status") or status_from_event(payload.get("event")),
        "value": charge.get("value"),
        "paidAt": charge.get("paidAt"),
        "expiresDate": charge.get("expiresDate"),
        "transactionID": charge.get("transactionID"),
        "identifier": charge.get("identifier"),
    }


def status_from_event(event: str | None) -> str | None:
    if not event:
        return None

    event = event.upper()
    if event.endswith("CHARGE_COMPLETED"):
        return "COMPLETED"
    if event.endswith("CHARGE_EXPIRED"):
        return "EXPIRED"
    if event.endswith("CHARGE_CREATED"):
        return "ACTIVE"
    return None


def simulated_webhook_payload(
    *,
    correlation_id: str,
    value: int,
    status: str,
    provider_charge_id: str | None,
    payment_link_id: str | None,
) -> dict[str, Any]:
    event = (
        "OPENPIX:CHARGE_COMPLETED"
        if status == "COMPLETED"
        else "OPENPIX:CHARGE_EXPIRED"
    )
    now = datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    charge: dict[str, Any] = {
        "value": value,
        "correlationID": correlation_id,
        "status": status,
    }
    if status == "COMPLETED":
        charge["paidAt"] = now
    if provider_charge_id:
        charge["identifier"] = provider_charge_id
        charge["transactionID"] = provider_charge_id
    if payment_link_id:
        charge["paymentLinkID"] = payment_link_id

    return {
        "event": event,
        "charge": charge,
        "pix": {
            "charge": charge,
            "value": value,
            "status": "CONFIRMED" if status == "COMPLETED" else "EXPIRED",
            "transactionID": provider_charge_id,
        },
    }

