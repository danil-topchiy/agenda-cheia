from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

import google.auth
from google.auth.exceptions import GoogleAuthError
from google.oauth2 import service_account
from googleapiclient.discovery import build

from app.schemas import AppointmentCreate, AppointmentResponse, AppointmentUpdate
from app.settings import Settings

APP_PROPERTY = "app"
APP_PROPERTY_VALUE = "agenda-cheia"
STATE_PROPERTY = "appointment_state"
EXTERNAL_ID_PROPERTY = "external_id"
SCOPES = ["https://www.googleapis.com/auth/calendar"]


class CalendarConfigurationError(RuntimeError):
    pass


class GoogleCalendarClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._service: Any | None = None

    @property
    def service(self) -> Any:
        if self._service is None:
            self._service = build(
                "calendar",
                "v3",
                credentials=self._credentials(),
                cache_discovery=False,
            )
        return self._service

    def _credentials(self) -> Any:
        try:
            if self.settings.google_credentials_file:
                credentials = service_account.Credentials.from_service_account_file(
                    self.settings.google_credentials_file,
                    scopes=SCOPES,
                )
            else:
                credentials, _ = google.auth.default(scopes=SCOPES)

            if self.settings.google_delegated_subject:
                credentials = credentials.with_subject(self.settings.google_delegated_subject)
        except (GoogleAuthError, OSError, ValueError) as exc:
            raise CalendarConfigurationError(
                "Google Calendar credentials are not configured. Set GOOGLE_CREDENTIALS_FILE "
                "or configure Google Application Default Credentials."
            ) from exc

        return credentials

    def create_event(self, body: dict[str, Any], send_updates: str = "none") -> dict[str, Any]:
        return (
            self.service.events()
            .insert(
                calendarId=self.settings.google_calendar_id,
                body=body,
                sendUpdates=send_updates,
            )
            .execute()
        )

    def get_event(self, event_id: str) -> dict[str, Any]:
        return (
            self.service.events()
            .get(calendarId=self.settings.google_calendar_id, eventId=event_id)
            .execute()
        )

    def patch_event(
        self,
        event_id: str,
        body: dict[str, Any],
        send_updates: str = "none",
    ) -> dict[str, Any]:
        return (
            self.service.events()
            .patch(
                calendarId=self.settings.google_calendar_id,
                eventId=event_id,
                body=body,
                sendUpdates=send_updates,
            )
            .execute()
        )

    def list_appointments(
        self,
        state: str | None = None,
        time_min: datetime | None = None,
        time_max: datetime | None = None,
        include_deleted: bool = False,
        max_results: int = 250,
    ) -> list[dict[str, Any]]:
        properties = [f"{APP_PROPERTY}={APP_PROPERTY_VALUE}"]
        if state:
            properties.append(f"{STATE_PROPERTY}={state}")

        params: dict[str, Any] = {
            "calendarId": self.settings.google_calendar_id,
            "privateExtendedProperty": properties,
            "singleEvents": True,
            "showDeleted": include_deleted,
            "maxResults": min(max_results, 2500),
            "orderBy": "startTime",
        }
        if time_min:
            params["timeMin"] = _rfc3339(time_min, self.settings.default_timezone)
        if time_max:
            params["timeMax"] = _rfc3339(time_max, self.settings.default_timezone)

        return self._list_all_event_pages(params)

    def list_changes(self, sync_token: str | None = None) -> tuple[list[dict[str, Any]], str | None]:
        params: dict[str, Any] = {
            "calendarId": self.settings.google_calendar_id,
            "showDeleted": True,
            "singleEvents": False,
            "maxResults": 2500,
        }
        if sync_token:
            params["syncToken"] = sync_token

        events: list[dict[str, Any]] = []
        next_sync_token: str | None = None
        while True:
            response = self.service.events().list(**params).execute()
            events.extend(response.get("items", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                next_sync_token = response.get("nextSyncToken")
                break
            params["pageToken"] = page_token

        return events, next_sync_token

    def watch_events(
        self,
        address: str,
        token: str | None,
        ttl_seconds: int,
    ) -> dict[str, Any]:
        expiration = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        body: dict[str, Any] = {
            "id": str(uuid4()),
            "type": "web_hook",
            "address": address,
            "expiration": int(expiration.timestamp() * 1000),
        }
        if token:
            body["token"] = token

        return (
            self.service.events()
            .watch(calendarId=self.settings.google_calendar_id, body=body)
            .execute()
        )

    def stop_channel(self, channel_id: str, resource_id: str) -> None:
        self.service.channels().stop(body={"id": channel_id, "resourceId": resource_id}).execute()

    def _list_all_event_pages(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        while True:
            response = self.service.events().list(**params).execute()
            events.extend(response.get("items", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                return events
            params["pageToken"] = page_token


def build_event_body(
    payload: AppointmentCreate | AppointmentUpdate,
    default_timezone: str,
    existing_private_properties: dict[str, str] | None = None,
    partial: bool = False,
) -> dict[str, Any]:
    data = payload.model_dump(exclude_unset=partial, exclude={"send_updates"})
    body: dict[str, Any] = {}

    _copy_if_present(data, body, "summary")
    _copy_if_present(data, body, "description")
    _copy_if_present(data, body, "location")

    time_zone = data.get("time_zone") or default_timezone
    if "start_at" in data and data["start_at"] is not None:
        body["start"] = _event_datetime(data["start_at"], time_zone)
    if "end_at" in data and data["end_at"] is not None:
        body["end"] = _event_datetime(data["end_at"], time_zone)

    if "attendees" in data and data["attendees"] is not None:
        body["attendees"] = [
            {
                "email": attendee["email"],
                **({"displayName": attendee["display_name"]} if attendee.get("display_name") else {}),
                "optional": attendee.get("optional", False),
            }
            for attendee in data["attendees"]
        ]

    if "calendar_status" in data and data["calendar_status"] is not None:
        body["status"] = _enum_value(data["calendar_status"])

    should_write_private_props = not partial or "state" in data or "external_id" in data
    if should_write_private_props:
        private_props = dict(existing_private_properties or {})
        private_props[APP_PROPERTY] = APP_PROPERTY_VALUE
        if "state" in data and data["state"] is not None:
            private_props[STATE_PROPERTY] = _enum_value(data["state"])
        if "external_id" in data:
            if data["external_id"] is None:
                private_props.pop(EXTERNAL_ID_PROPERTY, None)
            else:
                private_props[EXTERNAL_ID_PROPERTY] = data["external_id"]
        body["extendedProperties"] = {"private": private_props}

    return body


def is_agenda_cheia_event(event: dict[str, Any]) -> bool:
    private_props = private_properties(event)
    return (
        private_props.get(APP_PROPERTY) == APP_PROPERTY_VALUE
        or STATE_PROPERTY in private_props
    )


def private_properties(event: dict[str, Any]) -> dict[str, str]:
    return event.get("extendedProperties", {}).get("private", {}) or {}


def event_to_appointment_response(
    event: dict[str, Any],
    calendar_id: str,
    fallback_state: str = "scheduled",
) -> AppointmentResponse:
    private_props = private_properties(event)
    start_value, start_tz = _extract_event_datetime(event.get("start"))
    end_value, end_tz = _extract_event_datetime(event.get("end"))
    state = private_props.get(STATE_PROPERTY, fallback_state)
    google_status = event.get("status")
    deleted = google_status == "cancelled"

    return AppointmentResponse(
        appointment_id=event["id"],
        calendar_id=calendar_id,
        state=state,
        google_status=google_status,
        summary=event.get("summary"),
        description=event.get("description"),
        location=event.get("location"),
        start_at=start_value,
        end_at=end_value,
        time_zone=start_tz or end_tz,
        html_link=event.get("htmlLink"),
        etag=event.get("etag"),
        updated_at=_parse_google_datetime(event.get("updated")),
        deleted=deleted,
    )


def _copy_if_present(source: dict[str, Any], target: dict[str, Any], key: str) -> None:
    if key in source:
        target[key] = source[key]


def _event_datetime(value: datetime, time_zone: str) -> dict[str, str]:
    return {
        "dateTime": _rfc3339(value, time_zone),
        "timeZone": time_zone,
    }


def _rfc3339(value: datetime, default_timezone: str) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=ZoneInfo(default_timezone))
    return value.isoformat()


def _extract_event_datetime(data: dict[str, Any] | None) -> tuple[datetime | None, str | None]:
    if not data:
        return None, None
    value = data.get("dateTime") or data.get("date")
    if not value:
        return None, data.get("timeZone")
    return _parse_google_datetime(value), data.get("timeZone")


def _parse_google_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def _enum_value(value: Any) -> str:
    return getattr(value, "value", value)
