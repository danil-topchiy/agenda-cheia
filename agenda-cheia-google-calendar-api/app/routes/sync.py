from fastapi import APIRouter, Depends, HTTPException, status
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session

from app.dependencies import get_calendar_client, get_database
from app.google_calendar import GoogleCalendarClient
from app.repository import (
    latest_active_channel,
    list_channels,
    mark_channel_inactive,
    save_channel,
)
from app.schemas import (
    SyncRunResponse,
    WatchChannelResponse,
    WatchCreateRequest,
    WatchStopRequest,
)
from app.settings import Settings, get_settings
from app.sync_service import run_calendar_sync

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/poll", response_model=SyncRunResponse)
def poll_calendar_changes(
    force_full: bool = False,
    db: Session = Depends(get_database),
    client: GoogleCalendarClient = Depends(get_calendar_client),
) -> SyncRunResponse:
    try:
        return run_calendar_sync(db, client, force_full=force_full)
    except HttpError as exc:
        raise HTTPException(
            status_code=getattr(exc.resp, "status", status.HTTP_502_BAD_GATEWAY),
            detail=exc._get_reason(),
        ) from exc


@router.post("/watch", response_model=WatchChannelResponse, status_code=status.HTTP_201_CREATED)
def create_watch_channel(
    payload: WatchCreateRequest | None = None,
    db: Session = Depends(get_database),
    client: GoogleCalendarClient = Depends(get_calendar_client),
    settings: Settings = Depends(get_settings),
) -> WatchChannelResponse:
    payload = payload or WatchCreateRequest()
    address = str(payload.address) if payload.address else _default_webhook_address(settings)
    if not address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide address or configure GOOGLE_WEBHOOK_BASE_URL",
        )
    if not address.startswith("https://"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google Calendar push notifications require a public HTTPS webhook URL",
        )

    try:
        response = client.watch_events(
            address=address,
            token=payload.token or settings.google_webhook_token,
            ttl_seconds=payload.ttl_seconds or settings.watch_ttl_seconds,
        )
    except HttpError as exc:
        raise HTTPException(
            status_code=getattr(exc.resp, "status", status.HTTP_502_BAD_GATEWAY),
            detail=exc._get_reason(),
        ) from exc

    channel = save_channel(db, response)
    db.commit()
    return WatchChannelResponse(
        channel_id=channel.channel_id,
        resource_id=channel.resource_id,
        resource_uri=channel.resource_uri,
        expiration_ms=channel.expiration_ms,
        token=channel.token,
        active=channel.active,
    )


@router.get("/watch", response_model=list[WatchChannelResponse])
def get_watch_channels(db: Session = Depends(get_database)) -> list[WatchChannelResponse]:
    return list_channels(db)


@router.post("/watch/stop", status_code=status.HTTP_204_NO_CONTENT)
def stop_watch_channel(
    payload: WatchStopRequest | None = None,
    db: Session = Depends(get_database),
    client: GoogleCalendarClient = Depends(get_calendar_client),
) -> None:
    payload = payload or WatchStopRequest()
    channel_id = payload.channel_id
    resource_id = payload.resource_id

    if not channel_id or not resource_id:
        channel = latest_active_channel(db)
        if not channel:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active watch channel found")
        channel_id = channel.channel_id
        resource_id = channel.resource_id

    try:
        client.stop_channel(channel_id, resource_id)
    except HttpError as exc:
        raise HTTPException(
            status_code=getattr(exc.resp, "status", status.HTTP_502_BAD_GATEWAY),
            detail=exc._get_reason(),
        ) from exc

    mark_channel_inactive(db, channel_id)
    db.commit()


def _default_webhook_address(settings: Settings) -> str | None:
    if not settings.google_webhook_base_url:
        return None
    return settings.google_webhook_base_url.rstrip("/") + "/webhooks/google-calendar"

