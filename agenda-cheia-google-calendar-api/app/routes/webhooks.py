import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.dependencies import get_database
from app.repository import list_notifications, save_notification
from app.schemas import WebhookAck, WebhookNotificationResponse
from app.settings import Settings, get_settings
from app.sync_service import run_calendar_sync_in_new_session

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/google-calendar", response_model=WebhookAck, status_code=status.HTTP_202_ACCEPTED)
async def google_calendar_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database),
    settings: Settings = Depends(get_settings),
) -> WebhookAck:
    headers = {key.lower(): value for key, value in request.headers.items()}
    channel_token = headers.get("x-goog-channel-token")
    if settings.google_webhook_token and channel_token != settings.google_webhook_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Google channel token")

    save_notification(db, headers)
    db.commit()

    resource_state = headers.get("x-goog-resource-state")
    sync_scheduled = resource_state in {"sync", "exists", "not_exists"}
    if sync_scheduled:
        background_tasks.add_task(run_calendar_sync_in_new_session, False)

    return WebhookAck(
        accepted=True,
        resource_state=resource_state,
        sync_scheduled=sync_scheduled,
    )


@router.get("/google-calendar/notifications", response_model=list[WebhookNotificationResponse])
def google_calendar_notifications(
    after_id: int | None = None,
    limit: int = 50,
    db: Session = Depends(get_database),
) -> list[WebhookNotificationResponse]:
    return list_notifications(db, after_id=after_id, limit=max(1, min(limit, 200)))


@router.get("/google-calendar/stream")
async def google_calendar_notification_stream(
    after_id: int | None = None,
    poll_interval_seconds: float = 1.5,
    limit: int = 50,
) -> StreamingResponse:
    async def events():
        last_id = after_id
        interval = max(0.5, min(poll_interval_seconds, 10.0))
        batch_limit = max(1, min(limit, 200))
        yield "event: ready\ndata: {\"status\":\"connected\"}\n\n"
        while True:
            with SessionLocal() as db:
                rows = list_notifications(db, after_id=last_id, limit=batch_limit)
            for row in rows:
                last_id = row.id
                payload = row.model_dump_json()
                yield f"id: {row.id}\nevent: notification\ndata: {payload}\n\n"
            await asyncio.sleep(interval)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
