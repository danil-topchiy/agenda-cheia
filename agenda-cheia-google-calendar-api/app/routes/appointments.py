from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session

from app.dependencies import get_calendar_client, get_database
from app.google_calendar import (
    GoogleCalendarClient,
    build_event_body,
    event_to_appointment_response,
    private_properties,
)
from app.repository import list_appointments_from_mirror, upsert_appointment_from_event
from app.schemas import AppointmentCreate, AppointmentResponse, AppointmentState, AppointmentUpdate
from app.settings import Settings, get_settings

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def create_appointment(
    payload: AppointmentCreate,
    db: Session = Depends(get_database),
    client: GoogleCalendarClient = Depends(get_calendar_client),
    settings: Settings = Depends(get_settings),
) -> AppointmentResponse:
    body = build_event_body(payload, settings.default_timezone)
    try:
        event = client.create_event(body, send_updates=payload.send_updates)
    except HttpError as exc:
        raise _google_http_exception(exc) from exc

    upsert_appointment_from_event(db, event, settings.google_calendar_id)
    db.commit()
    return event_to_appointment_response(event, settings.google_calendar_id)


@router.get("", response_model=list[AppointmentResponse])
def list_appointments(
    state: AppointmentState | None = Query(default=None),
    source: Literal["google", "local"] = Query(default="google"),
    include_deleted: bool = Query(default=False),
    time_min: datetime | None = Query(default=None),
    time_max: datetime | None = Query(default=None),
    max_results: int = Query(default=250, ge=1, le=2500),
    db: Session = Depends(get_database),
    client: GoogleCalendarClient = Depends(get_calendar_client),
    settings: Settings = Depends(get_settings),
) -> list[AppointmentResponse]:
    state_value = state.value if state else None
    if source == "local":
        return list_appointments_from_mirror(
            db,
            settings.google_calendar_id,
            state_value,
            include_deleted=include_deleted,
        )

    try:
        events = client.list_appointments(
            state=state_value,
            time_min=time_min,
            time_max=time_max,
            include_deleted=include_deleted,
            max_results=max_results,
        )
    except HttpError as exc:
        raise _google_http_exception(exc) from exc

    return [
        event_to_appointment_response(event, settings.google_calendar_id)
        for event in events
    ]


@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: str,
    client: GoogleCalendarClient = Depends(get_calendar_client),
    settings: Settings = Depends(get_settings),
) -> AppointmentResponse:
    try:
        event = client.get_event(appointment_id)
    except HttpError as exc:
        raise _google_http_exception(exc) from exc

    return event_to_appointment_response(event, settings.google_calendar_id)


@router.patch("/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(
    appointment_id: str,
    payload: AppointmentUpdate,
    db: Session = Depends(get_database),
    client: GoogleCalendarClient = Depends(get_calendar_client),
    settings: Settings = Depends(get_settings),
) -> AppointmentResponse:
    try:
        existing_event = client.get_event(appointment_id)
        body = build_event_body(
            payload,
            settings.default_timezone,
            existing_private_properties=private_properties(existing_event),
            partial=True,
        )
        if not body:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No appointment fields were provided for update",
            )
        event = client.patch_event(appointment_id, body, send_updates=payload.send_updates)
    except HttpError as exc:
        raise _google_http_exception(exc) from exc

    upsert_appointment_from_event(db, event, settings.google_calendar_id)
    db.commit()
    return event_to_appointment_response(event, settings.google_calendar_id)


def _google_http_exception(exc: HttpError) -> HTTPException:
    return HTTPException(
        status_code=getattr(exc.resp, "status", status.HTTP_502_BAD_GATEWAY),
        detail=exc._get_reason(),
    )

