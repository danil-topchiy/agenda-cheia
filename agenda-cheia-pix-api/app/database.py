import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from app.config import Settings


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def init_db(settings: Settings) -> None:
    db_path = Path(settings.database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with connect(settings) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS charges (
                correlation_id TEXT PRIMARY KEY,
                value INTEGER,
                status TEXT,
                expires_in INTEGER,
                expires_date TEXT,
                br_code TEXT,
                qr_code_image TEXT,
                payment_link_url TEXT,
                provider_charge_id TEXT,
                payment_link_id TEXT,
                paid_at TEXT,
                raw_response TEXT,
                raw_webhook TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS webhook_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event TEXT,
                correlation_id TEXT,
                raw_payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


@contextmanager
def connect(settings: Settings) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def upsert_charge_from_provider(
    settings: Settings,
    *,
    request_payload: dict[str, Any],
    provider_response: dict[str, Any],
) -> dict[str, Any]:
    charge = provider_response.get("charge") or {}
    correlation_id = (
        charge.get("correlationID")
        or provider_response.get("correlationID")
        or request_payload["correlationID"]
    )
    now = utc_now()
    data = {
        "correlation_id": correlation_id,
        "value": charge.get("value") or request_payload.get("value"),
        "status": charge.get("status"),
        "expires_in": charge.get("expiresIn") or request_payload.get("expiresIn"),
        "expires_date": charge.get("expiresDate"),
        "br_code": charge.get("brCode") or provider_response.get("brCode"),
        "qr_code_image": charge.get("qrCodeImage"),
        "payment_link_url": charge.get("paymentLinkUrl"),
        "provider_charge_id": charge.get("identifier") or charge.get("transactionID"),
        "payment_link_id": charge.get("paymentLinkID"),
        "paid_at": charge.get("paidAt"),
        "raw_response": json.dumps(provider_response, ensure_ascii=False),
        "raw_webhook": None,
        "created_at": now,
        "updated_at": now,
    }

    with connect(settings) as conn:
        conn.execute(
            """
            INSERT INTO charges (
                correlation_id, value, status, expires_in, expires_date, br_code,
                qr_code_image, payment_link_url, provider_charge_id, payment_link_id,
                paid_at, raw_response, raw_webhook, created_at, updated_at
            )
            VALUES (
                :correlation_id, :value, :status, :expires_in, :expires_date, :br_code,
                :qr_code_image, :payment_link_url, :provider_charge_id,
                :payment_link_id, :paid_at, :raw_response, :raw_webhook,
                :created_at, :updated_at
            )
            ON CONFLICT(correlation_id) DO UPDATE SET
                value = excluded.value,
                status = excluded.status,
                expires_in = excluded.expires_in,
                expires_date = excluded.expires_date,
                br_code = excluded.br_code,
                qr_code_image = excluded.qr_code_image,
                payment_link_url = excluded.payment_link_url,
                provider_charge_id = excluded.provider_charge_id,
                payment_link_id = excluded.payment_link_id,
                paid_at = COALESCE(excluded.paid_at, charges.paid_at),
                raw_response = excluded.raw_response,
                updated_at = excluded.updated_at
            """,
            data,
        )
        conn.commit()

    return data


def get_charge(settings: Settings, correlation_id: str) -> dict[str, Any] | None:
    with connect(settings) as conn:
        row = conn.execute(
            """
            SELECT
                correlation_id, value, status, expires_in, expires_date, br_code,
                qr_code_image, payment_link_url, provider_charge_id, payment_link_id,
                paid_at, created_at, updated_at
            FROM charges
            WHERE correlation_id = ?
            """,
            (correlation_id,),
        ).fetchone()
    return dict(row) if row else None


def save_webhook_event(settings: Settings, payload: dict[str, Any]) -> dict[str, Any]:
    event = payload.get("event")
    charge = extract_charge(payload)
    correlation_id = charge.get("correlationID") if charge else None
    status = extract_status(event=event, charge=charge)
    now = utc_now()
    raw_payload = json.dumps(payload, ensure_ascii=False)

    with connect(settings) as conn:
        conn.execute(
            """
            INSERT INTO webhook_events (event, correlation_id, raw_payload, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (event, correlation_id, raw_payload, now),
        )
        if correlation_id:
            conn.execute(
                """
                INSERT INTO charges (
                    correlation_id, value, status, expires_in, expires_date, br_code,
                    qr_code_image, payment_link_url, provider_charge_id,
                    payment_link_id, paid_at, raw_response, raw_webhook,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?)
                ON CONFLICT(correlation_id) DO UPDATE SET
                    value = COALESCE(excluded.value, charges.value),
                    status = COALESCE(excluded.status, charges.status),
                    expires_in = COALESCE(excluded.expires_in, charges.expires_in),
                    expires_date = COALESCE(excluded.expires_date, charges.expires_date),
                    br_code = COALESCE(excluded.br_code, charges.br_code),
                    qr_code_image = COALESCE(excluded.qr_code_image, charges.qr_code_image),
                    payment_link_url = COALESCE(excluded.payment_link_url, charges.payment_link_url),
                    provider_charge_id = COALESCE(excluded.provider_charge_id, charges.provider_charge_id),
                    payment_link_id = COALESCE(excluded.payment_link_id, charges.payment_link_id),
                    paid_at = COALESCE(excluded.paid_at, charges.paid_at),
                    raw_webhook = excluded.raw_webhook,
                    updated_at = excluded.updated_at
                """,
                (
                    correlation_id,
                    charge.get("value"),
                    status,
                    charge.get("expiresIn"),
                    charge.get("expiresDate"),
                    charge.get("brCode"),
                    charge.get("qrCodeImage"),
                    charge.get("paymentLinkUrl"),
                    charge.get("identifier") or charge.get("transactionID"),
                    charge.get("paymentLinkID"),
                    charge.get("paidAt"),
                    raw_payload,
                    now,
                    now,
                ),
            )
        conn.commit()

    return {"event": event, "correlation_id": correlation_id, "status": status}


def extract_charge(payload: dict[str, Any]) -> dict[str, Any]:
    charge = payload.get("charge")
    if isinstance(charge, dict):
        return charge

    pix = payload.get("pix")
    if isinstance(pix, dict) and isinstance(pix.get("charge"), dict):
        return pix["charge"]

    return {}


def extract_status(event: str | None, charge: dict[str, Any]) -> str | None:
    if charge.get("status"):
        return charge["status"]
    if not event:
        return None

    normalized = event.upper()
    if normalized.endswith("CHARGE_COMPLETED"):
        return "COMPLETED"
    if normalized.endswith("CHARGE_EXPIRED"):
        return "EXPIRED"
    if normalized.endswith("CHARGE_CREATED"):
        return "ACTIVE"
    return None

