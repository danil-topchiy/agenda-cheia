from datetime import datetime

from app.google_calendar import APP_PROPERTY, APP_PROPERTY_VALUE, STATE_PROPERTY, build_event_body
from app.schemas import AppointmentCreate, AppointmentState, AppointmentUpdate


def test_build_create_event_body_writes_private_state() -> None:
    payload = AppointmentCreate(
        summary="Consulta",
        start_at=datetime.fromisoformat("2026-08-20T14:00:00-03:00"),
        end_at=datetime.fromisoformat("2026-08-20T15:00:00-03:00"),
        state=AppointmentState.confirmed,
    )

    body = build_event_body(payload, "America/Sao_Paulo")

    assert body["summary"] == "Consulta"
    assert body["extendedProperties"]["private"][APP_PROPERTY] == APP_PROPERTY_VALUE
    assert body["extendedProperties"]["private"][STATE_PROPERTY] == "confirmed"
    assert body["start"]["timeZone"] == "America/Sao_Paulo"


def test_build_update_event_body_preserves_existing_private_props() -> None:
    payload = AppointmentUpdate(state=AppointmentState.completed)

    body = build_event_body(
        payload,
        "America/Sao_Paulo",
        existing_private_properties={"custom": "keep"},
        partial=True,
    )

    private_props = body["extendedProperties"]["private"]
    assert private_props["custom"] == "keep"
    assert private_props[STATE_PROPERTY] == "completed"

