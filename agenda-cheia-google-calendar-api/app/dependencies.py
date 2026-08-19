from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.google_calendar import GoogleCalendarClient
from app.settings import Settings, get_settings


def get_calendar_client(settings: Settings = Depends(get_settings)) -> GoogleCalendarClient:
    return GoogleCalendarClient(settings)


def get_database() -> Generator[Session, None, None]:
    yield from get_db()

