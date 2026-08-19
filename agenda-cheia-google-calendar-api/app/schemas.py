from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, HttpUrl, model_validator


class AppointmentState(str, Enum):
    scheduled = "scheduled"
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"
    no_show = "no_show"


class CalendarEventStatus(str, Enum):
    confirmed = "confirmed"
    tentative = "tentative"
    cancelled = "cancelled"


SendUpdates = Literal["all", "externalOnly", "none"]


class Attendee(BaseModel):
    email: EmailStr
    display_name: str | None = None
    optional: bool = False


class AppointmentBase(BaseModel):
    summary: str | None = Field(default=None, min_length=1, max_length=512)
    description: str | None = None
    location: str | None = Field(default=None, max_length=512)
    start_at: datetime | None = None
    end_at: datetime | None = None
    time_zone: str | None = Field(default=None, max_length=128)
    state: AppointmentState | None = None
    calendar_status: CalendarEventStatus | None = None
    external_id: str | None = Field(default=None, max_length=256)
    attendees: list[Attendee] | None = None

    @model_validator(mode="after")
    def validate_time_range(self) -> "AppointmentBase":
        if self.start_at is None or self.end_at is None:
            return self

        start = self.start_at
        end = self.end_at
        if _is_aware(start) != _is_aware(end):
            raise ValueError("start_at and end_at must both include timezone info, or both omit it")

        comparable_start = start.astimezone(timezone.utc) if _is_aware(start) else start
        comparable_end = end.astimezone(timezone.utc) if _is_aware(end) else end
        if comparable_end <= comparable_start:
            raise ValueError("end_at must be greater than start_at")
        return self


class AppointmentCreate(AppointmentBase):
    summary: str = Field(min_length=1, max_length=512)
    start_at: datetime
    end_at: datetime
    state: AppointmentState = AppointmentState.scheduled
    attendees: list[Attendee] = Field(default_factory=list)
    send_updates: SendUpdates = "none"


class AppointmentUpdate(AppointmentBase):
    send_updates: SendUpdates = "none"


class AppointmentResponse(BaseModel):
    appointment_id: str
    calendar_id: str
    state: str
    google_status: str | None = None
    summary: str | None = None
    description: str | None = None
    location: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    time_zone: str | None = None
    html_link: str | None = None
    etag: str | None = None
    updated_at: datetime | None = None
    deleted: bool = False


class AppointmentChange(BaseModel):
    change_type: Literal["created", "updated", "deleted"]
    appointment: AppointmentResponse


class SyncRunResponse(BaseModel):
    calendar_id: str
    full_sync: bool
    changes_count: int
    next_sync_token_saved: bool
    changes: list[AppointmentChange]


class WatchCreateRequest(BaseModel):
    address: HttpUrl | None = None
    token: str | None = Field(default=None, max_length=256)
    ttl_seconds: int | None = Field(default=None, ge=60)


class WatchChannelResponse(BaseModel):
    channel_id: str
    resource_id: str
    resource_uri: str | None = None
    expiration_ms: int | None = None
    token: str | None = None
    active: bool = True


class WatchStopRequest(BaseModel):
    channel_id: str | None = None
    resource_id: str | None = None


class WebhookAck(BaseModel):
    accepted: bool
    resource_state: str | None = None
    sync_scheduled: bool = False


def _is_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None

