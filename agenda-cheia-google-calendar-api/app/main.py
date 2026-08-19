from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.database import init_db
from app.google_calendar import CalendarConfigurationError
from app.routes import appointments, sync, webhooks
from app.settings import get_settings
from app.sync_service import run_calendar_sync_in_new_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    settings = get_settings()
    polling_task: asyncio.Task[None] | None = None
    if settings.enable_polling_on_startup:
        polling_task = asyncio.create_task(_polling_loop(settings.poll_interval_seconds))
        app.state.polling_task = polling_task

    yield

    if polling_task:
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title=get_settings().app_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(appointments.router)
app.include_router(sync.router)
app.include_router(webhooks.router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(CalendarConfigurationError)
async def calendar_configuration_error(
    request: Request,
    exc: CalendarConfigurationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": str(exc)},
    )


async def _polling_loop(interval_seconds: int) -> None:
    while True:
        await asyncio.to_thread(run_calendar_sync_in_new_session, False)
        await asyncio.sleep(interval_seconds)
