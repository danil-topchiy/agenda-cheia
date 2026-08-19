from __future__ import annotations

import logging

from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.google_calendar import GoogleCalendarClient
from app.repository import (
    clear_appointment_mirror,
    clear_sync_token,
    get_sync_token,
    set_sync_token,
    upsert_appointment_from_event,
)
from app.schemas import AppointmentChange, SyncRunResponse
from app.settings import get_settings

logger = logging.getLogger(__name__)


def run_calendar_sync(
    db: Session,
    client: GoogleCalendarClient,
    force_full: bool = False,
) -> SyncRunResponse:
    calendar_id = client.settings.google_calendar_id
    sync_token = None if force_full else get_sync_token(db, calendar_id)
    full_sync = force_full or sync_token is None
    if force_full:
        clear_appointment_mirror(db, calendar_id)
        clear_sync_token(db, calendar_id)

    try:
        events, next_sync_token = client.list_changes(sync_token=sync_token)
    except HttpError as exc:
        if getattr(exc.resp, "status", None) != 410:
            raise
        clear_sync_token(db, calendar_id)
        clear_appointment_mirror(db, calendar_id)
        events, next_sync_token = client.list_changes(sync_token=None)
        full_sync = True

    changes: list[AppointmentChange] = []
    for event in events:
        change = upsert_appointment_from_event(db, event, calendar_id)
        if change is not None:
            changes.append(change)

    if next_sync_token:
        set_sync_token(db, calendar_id, next_sync_token)

    db.commit()
    return SyncRunResponse(
        calendar_id=calendar_id,
        full_sync=full_sync,
        changes_count=len(changes),
        next_sync_token_saved=bool(next_sync_token),
        changes=changes,
    )


def run_calendar_sync_in_new_session(force_full: bool = False) -> None:
    settings = get_settings()
    with SessionLocal() as db:
        client = GoogleCalendarClient(settings)
        try:
            result = run_calendar_sync(db, client, force_full=force_full)
            logger.info("calendar sync completed with %s changes", result.changes_count)
        except Exception:
            logger.exception("calendar sync failed")
