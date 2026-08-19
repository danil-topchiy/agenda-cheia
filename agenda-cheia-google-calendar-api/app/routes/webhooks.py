from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.dependencies import get_database
from app.repository import save_notification
from app.schemas import WebhookAck
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

