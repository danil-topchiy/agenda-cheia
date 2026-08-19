from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.google_calendar import (
    event_to_appointment_response,
    is_agenda_cheia_event,
    private_properties,
)
from app.models import AppointmentMirror, SyncState, WebhookChannel, WebhookNotification
from app.schemas import AppointmentChange, AppointmentResponse, WatchChannelResponse


def sync_token_key(calendar_id: str) -> str:
    return f"calendar_events_sync_token:{calendar_id}"


def get_sync_token(db: Session, calendar_id: str) -> str | None:
    state = db.get(SyncState, sync_token_key(calendar_id))
    return state.value if state else None


def set_sync_token(db: Session, calendar_id: str, token: str) -> None:
    key = sync_token_key(calendar_id)
    state = db.get(SyncState, key)
    if state:
        state.value = token
    else:
        db.add(SyncState(key=key, value=token))


def clear_sync_token(db: Session, calendar_id: str) -> None:
    state = db.get(SyncState, sync_token_key(calendar_id))
    if state:
        db.delete(state)


def clear_appointment_mirror(db: Session, calendar_id: str) -> None:
    db.execute(delete(AppointmentMirror).where(AppointmentMirror.calendar_id == calendar_id))


def upsert_appointment_from_event(
    db: Session,
    event: dict[str, Any],
    calendar_id: str,
) -> AppointmentChange | None:
    event_id = event.get("id")
    if not event_id:
        return None

    existing = db.get(AppointmentMirror, event_id)
    if not existing and not is_agenda_cheia_event(event):
        return None

    fallback_state = existing.state if existing else "scheduled"
    appointment = event_to_appointment_response(event, calendar_id, fallback_state=fallback_state)
    raw_json = json.dumps(event, ensure_ascii=True, sort_keys=True)
    change_type = _change_type(existing, appointment, raw_json)

    if existing is None:
        existing = AppointmentMirror(google_event_id=event_id, calendar_id=calendar_id, state=appointment.state)
        db.add(existing)

    existing.calendar_id = calendar_id
    existing.state = appointment.state
    existing.google_status = appointment.google_status
    existing.summary = appointment.summary
    existing.description = appointment.description
    existing.location = appointment.location
    existing.start_at = appointment.start_at
    existing.end_at = appointment.end_at
    existing.time_zone = appointment.time_zone
    existing.html_link = appointment.html_link
    existing.etag = appointment.etag
    existing.google_updated_at = appointment.updated_at
    existing.deleted = appointment.deleted
    existing.raw_json = raw_json

    return AppointmentChange(change_type=change_type, appointment=appointment)


def list_appointments_from_mirror(
    db: Session,
    calendar_id: str,
    state: str | None,
    include_deleted: bool,
) -> list[AppointmentResponse]:
    stmt = select(AppointmentMirror).where(AppointmentMirror.calendar_id == calendar_id)
    if state:
        stmt = stmt.where(AppointmentMirror.state == state)
    if not include_deleted:
        stmt = stmt.where(AppointmentMirror.deleted.is_(False))
    stmt = stmt.order_by(AppointmentMirror.start_at.asc().nulls_last())

    return [_row_to_response(row) for row in db.scalars(stmt).all()]


def save_channel(db: Session, response: dict[str, Any]) -> WebhookChannel:
    channel = WebhookChannel(
        channel_id=response["id"],
        resource_id=response["resourceId"],
        resource_uri=response.get("resourceUri"),
        token=response.get("token"),
        expiration_ms=_int_or_none(response.get("expiration")),
        active=True,
    )
    db.add(channel)
    return channel


def latest_active_channel(db: Session) -> WebhookChannel | None:
    stmt = (
        select(WebhookChannel)
        .where(WebhookChannel.active.is_(True))
        .order_by(WebhookChannel.created_at.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()


def mark_channel_inactive(db: Session, channel_id: str) -> None:
    stmt = select(WebhookChannel).where(WebhookChannel.channel_id == channel_id)
    channel = db.scalars(stmt).first()
    if channel:
        channel.active = False


def list_channels(db: Session) -> list[WatchChannelResponse]:
    stmt = select(WebhookChannel).order_by(WebhookChannel.created_at.desc())
    rows = db.scalars(stmt).all()
    return [
        WatchChannelResponse(
            channel_id=row.channel_id,
            resource_id=row.resource_id,
            resource_uri=row.resource_uri,
            expiration_ms=row.expiration_ms,
            token=row.token,
            active=row.active,
        )
        for row in rows
    ]


def save_notification(db: Session, headers: dict[str, str | None]) -> WebhookNotification:
    notification = WebhookNotification(
        channel_id=headers.get("x-goog-channel-id"),
        resource_id=headers.get("x-goog-resource-id"),
        resource_state=headers.get("x-goog-resource-state"),
        resource_uri=headers.get("x-goog-resource-uri"),
        message_number=headers.get("x-goog-message-number"),
        channel_token=headers.get("x-goog-channel-token"),
    )
    db.add(notification)
    return notification


def _change_type(
    existing: AppointmentMirror | None,
    appointment: AppointmentResponse,
    raw_json: str,
) -> str:
    if appointment.deleted:
        return "deleted"
    if existing is None:
        return "created"
    if existing.raw_json != raw_json:
        return "updated"
    return "updated"


def _row_to_response(row: AppointmentMirror) -> AppointmentResponse:
    return AppointmentResponse(
        appointment_id=row.google_event_id,
        calendar_id=row.calendar_id,
        state=row.state,
        google_status=row.google_status,
        summary=row.summary,
        description=row.description,
        location=row.location,
        start_at=row.start_at,
        end_at=row.end_at,
        time_zone=row.time_zone,
        html_link=row.html_link,
        etag=row.etag,
        updated_at=row.google_updated_at,
        deleted=row.deleted,
    )


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)
