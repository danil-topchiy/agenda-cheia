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
from app.models import (
    AppointmentMirror,
    GoogleOAuthConnection,
    GoogleOAuthState,
    SyncState,
    WebhookChannel,
    WebhookNotification,
)
from app.schemas import (
    AppointmentChange,
    AppointmentResponse,
    WatchChannelResponse,
    WebhookNotificationResponse,
)


def sync_token_key(calendar_id: str, user_id: str | None = None) -> str:
    owner = user_id or "service-account"
    return f"calendar_events_sync_token:{owner}:{calendar_id}"


def get_sync_token(db: Session, calendar_id: str, user_id: str | None = None) -> str | None:
    state = db.get(SyncState, sync_token_key(calendar_id, user_id))
    return state.value if state else None


def set_sync_token(db: Session, calendar_id: str, token: str, user_id: str | None = None) -> None:
    key = sync_token_key(calendar_id, user_id)
    state = db.get(SyncState, key)
    if state:
        state.value = token
    else:
        db.add(SyncState(key=key, value=token))


def clear_sync_token(db: Session, calendar_id: str, user_id: str | None = None) -> None:
    state = db.get(SyncState, sync_token_key(calendar_id, user_id))
    if state:
        db.delete(state)


def clear_appointment_mirror(db: Session, calendar_id: str, user_id: str | None = None) -> None:
    stmt = delete(AppointmentMirror).where(AppointmentMirror.calendar_id == calendar_id)
    if user_id is not None:
        stmt = stmt.where(AppointmentMirror.user_id == user_id)
    db.execute(stmt)


def upsert_appointment_from_event(
    db: Session,
    event: dict[str, Any],
    calendar_id: str,
    user_id: str | None = None,
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
        existing = AppointmentMirror(
            google_event_id=event_id,
            user_id=user_id,
            calendar_id=calendar_id,
            state=appointment.state,
        )
        db.add(existing)

    existing.user_id = user_id
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
    user_id: str | None = None,
) -> list[AppointmentResponse]:
    stmt = select(AppointmentMirror).where(AppointmentMirror.calendar_id == calendar_id)
    if user_id is not None:
        stmt = stmt.where(AppointmentMirror.user_id == user_id)
    if state:
        stmt = stmt.where(AppointmentMirror.state == state)
    if not include_deleted:
        stmt = stmt.where(AppointmentMirror.deleted.is_(False))
    stmt = stmt.order_by(AppointmentMirror.start_at.asc().nulls_last())

    return [_row_to_response(row) for row in db.scalars(stmt).all()]


def save_channel(
    db: Session,
    response: dict[str, Any],
    user_id: str | None = None,
    calendar_id: str | None = None,
) -> WebhookChannel:
    channel = WebhookChannel(
        user_id=user_id,
        calendar_id=calendar_id,
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


def get_channel_by_channel_id(db: Session, channel_id: str | None) -> WebhookChannel | None:
    if not channel_id:
        return None
    stmt = select(WebhookChannel).where(WebhookChannel.channel_id == channel_id)
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
            user_id=row.user_id,
            calendar_id=row.calendar_id,
            channel_id=row.channel_id,
            resource_id=row.resource_id,
            resource_uri=row.resource_uri,
            expiration_ms=row.expiration_ms,
            token=row.token,
            active=row.active,
        )
        for row in rows
    ]


def save_notification(
    db: Session,
    headers: dict[str, str | None],
    user_id: str | None = None,
    calendar_id: str | None = None,
) -> WebhookNotification:
    notification = WebhookNotification(
        user_id=user_id,
        calendar_id=calendar_id,
        channel_id=headers.get("x-goog-channel-id"),
        resource_id=headers.get("x-goog-resource-id"),
        resource_state=headers.get("x-goog-resource-state"),
        resource_uri=headers.get("x-goog-resource-uri"),
        message_number=headers.get("x-goog-message-number"),
        channel_token=headers.get("x-goog-channel-token"),
    )
    db.add(notification)
    return notification


def list_notifications(
    db: Session,
    after_id: int | None = None,
    limit: int = 50,
) -> list[WebhookNotificationResponse]:
    stmt = select(WebhookNotification)
    if after_id is not None:
        stmt = stmt.where(WebhookNotification.id > after_id)
    stmt = stmt.order_by(WebhookNotification.id.desc()).limit(limit)
    rows = list(db.scalars(stmt).all())
    rows.reverse()
    return [
        WebhookNotificationResponse(
            id=row.id,
            user_id=row.user_id,
            calendar_id=row.calendar_id,
            channel_id=row.channel_id,
            resource_id=row.resource_id,
            resource_state=row.resource_state,
            resource_uri=row.resource_uri,
            message_number=row.message_number,
            channel_token=row.channel_token,
            received_at=row.received_at,
        )
        for row in rows
    ]


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


def save_oauth_state(
    db: Session,
    state: str,
    user_id: str,
    calendar_id: str,
    redirect_after: str | None,
) -> GoogleOAuthState:
    row = GoogleOAuthState(
        state=state,
        user_id=user_id,
        calendar_id=calendar_id,
        redirect_after=redirect_after,
    )
    db.add(row)
    return row


def pop_oauth_state(db: Session, state: str) -> GoogleOAuthState | None:
    row = db.get(GoogleOAuthState, state)
    if row is not None:
        db.delete(row)
    return row


def get_oauth_connection(db: Session, user_id: str) -> GoogleOAuthConnection | None:
    return db.get(GoogleOAuthConnection, user_id)


def list_oauth_connections(db: Session) -> list[GoogleOAuthConnection]:
    stmt = select(GoogleOAuthConnection).order_by(GoogleOAuthConnection.updated_at.desc())
    return list(db.scalars(stmt).all())


def save_oauth_connection(db: Session, connection: GoogleOAuthConnection) -> GoogleOAuthConnection:
    existing = db.get(GoogleOAuthConnection, connection.user_id)
    if existing is None:
        db.add(connection)
        return connection

    existing.google_email = connection.google_email
    existing.calendar_id = connection.calendar_id
    existing.scopes = connection.scopes
    existing.access_token = connection.access_token
    existing.refresh_token = connection.refresh_token or existing.refresh_token
    existing.token_uri = connection.token_uri
    existing.client_id = connection.client_id
    existing.client_secret = connection.client_secret
    existing.expiry = connection.expiry
    return existing


def delete_oauth_connection(db: Session, user_id: str) -> bool:
    connection = db.get(GoogleOAuthConnection, user_id)
    if connection is None:
        return False
    db.delete(connection)
    return True
