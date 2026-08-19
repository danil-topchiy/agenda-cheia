from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas import AppointmentCreate


def test_appointment_create_rejects_invalid_time_range() -> None:
    with pytest.raises(ValidationError):
        AppointmentCreate(
            summary="Consulta",
            start_at=datetime.fromisoformat("2026-08-20T15:00:00-03:00"),
            end_at=datetime.fromisoformat("2026-08-20T14:00:00-03:00"),
        )


def test_appointment_create_accepts_valid_time_range() -> None:
    payload = AppointmentCreate(
        summary="Consulta",
        start_at=datetime.fromisoformat("2026-08-20T14:00:00-03:00"),
        end_at=datetime.fromisoformat("2026-08-20T15:00:00-03:00"),
    )

    assert payload.summary == "Consulta"
