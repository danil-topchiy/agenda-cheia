from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from google.auth.transport.requests import AuthorizedSession
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from sqlalchemy.orm import Session

from app.google_calendar import CalendarConfigurationError, GoogleCalendarClient
from app.models import GoogleOAuthConnection
from app.repository import (
    get_oauth_connection,
    list_oauth_connections,
    pop_oauth_state,
    save_oauth_connection,
    save_oauth_state,
)
from app.schemas import OAuthConnectionResponse
from app.settings import Settings

GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def oauth_scopes(settings: Settings) -> list[str]:
    return [scope for scope in settings.google_oauth_scopes.split() if scope]


def create_authorization_url(
    db: Session,
    settings: Settings,
    user_id: str,
    calendar_id: str = "primary",
    redirect_after: str | None = None,
) -> tuple[str, str]:
    state = str(uuid4())
    flow = _build_flow(settings)
    authorization_kwargs: dict[str, Any] = {
        "access_type": "offline",
        "include_granted_scopes": "true",
        "state": state,
    }
    if settings.google_oauth_prompt_consent:
        authorization_kwargs["prompt"] = "consent"

    authorization_url, returned_state = flow.authorization_url(**authorization_kwargs)
    save_oauth_state(
        db,
        state=returned_state,
        user_id=user_id,
        calendar_id=calendar_id,
        redirect_after=redirect_after,
    )
    db.commit()
    return authorization_url, returned_state


def handle_oauth_callback(
    db: Session,
    settings: Settings,
    state: str,
    authorization_response: str,
) -> GoogleOAuthConnection:
    oauth_state = pop_oauth_state(db, state)
    if oauth_state is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OAuth state")

    flow = _build_flow(settings)
    flow.fetch_token(authorization_response=authorization_response)
    credentials = flow.credentials
    google_email = _fetch_google_email(credentials)
    client_id, client_secret = _client_credentials(settings)

    connection = GoogleOAuthConnection(
        user_id=oauth_state.user_id,
        google_email=google_email,
        calendar_id=oauth_state.calendar_id,
        scopes=json.dumps(list(credentials.scopes or oauth_scopes(settings))),
        access_token=credentials.token,
        refresh_token=credentials.refresh_token,
        token_uri=credentials.token_uri or GOOGLE_TOKEN_URI,
        client_id=client_id,
        client_secret=client_secret,
        expiry=_normalize_expiry(credentials.expiry),
    )
    saved = save_oauth_connection(db, connection)
    db.commit()
    return saved


def oauth_connection_to_response(connection: GoogleOAuthConnection) -> OAuthConnectionResponse:
    return OAuthConnectionResponse(
        user_id=connection.user_id,
        google_email=connection.google_email,
        calendar_id=connection.calendar_id,
        scopes=json.loads(connection.scopes),
        connected=bool(connection.refresh_token or connection.access_token),
        expiry=connection.expiry,
        updated_at=connection.updated_at,
    )


def list_oauth_connection_responses(db: Session) -> list[OAuthConnectionResponse]:
    return [oauth_connection_to_response(connection) for connection in list_oauth_connections(db)]


def calendar_client_for_user(
    db: Session,
    settings: Settings,
    user_id: str | None = None,
    calendar_id: str | None = None,
) -> GoogleCalendarClient:
    if user_id is None:
        return GoogleCalendarClient(settings, calendar_id=calendar_id)

    connection = get_oauth_connection(db, user_id)
    if connection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Google OAuth connection not found for user_id={user_id}",
        )

    credentials = credentials_from_connection(connection)

    def persist_refreshed_credentials(updated_credentials: Credentials) -> None:
        update_connection_from_credentials(connection, updated_credentials)
        db.add(connection)
        db.commit()

    return GoogleCalendarClient(
        settings,
        credentials=credentials,
        calendar_id=calendar_id or connection.calendar_id or settings.google_calendar_id,
        after_execute=persist_refreshed_credentials,
    )


def credentials_from_connection(connection: GoogleOAuthConnection) -> Credentials:
    return Credentials(
        token=connection.access_token,
        refresh_token=connection.refresh_token,
        token_uri=connection.token_uri,
        client_id=connection.client_id,
        client_secret=connection.client_secret,
        scopes=json.loads(connection.scopes),
    )


def update_connection_from_credentials(
    connection: GoogleOAuthConnection,
    credentials: Credentials,
) -> None:
    connection.access_token = credentials.token
    if credentials.refresh_token:
        connection.refresh_token = credentials.refresh_token
    connection.expiry = _normalize_expiry(credentials.expiry)


def _build_flow(settings: Settings) -> Flow:
    scopes = oauth_scopes(settings)
    if settings.google_oauth_client_secrets_file:
        flow = Flow.from_client_secrets_file(settings.google_oauth_client_secrets_file, scopes=scopes)
    else:
        flow = Flow.from_client_config(_client_config(settings), scopes=scopes)
    flow.redirect_uri = settings.google_oauth_redirect_uri
    return flow


def _client_config(settings: Settings) -> dict[str, Any]:
    client_id, client_secret = _client_credentials(settings)
    return {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": GOOGLE_TOKEN_URI,
            "redirect_uris": [settings.google_oauth_redirect_uri],
        }
    }


def _client_credentials(settings: Settings) -> tuple[str, str]:
    if settings.google_oauth_client_id and settings.google_oauth_client_secret:
        return settings.google_oauth_client_id, settings.google_oauth_client_secret

    if settings.google_oauth_client_secrets_file:
        with open(settings.google_oauth_client_secrets_file) as file:
            data = json.load(file)
        web_config = data.get("web") or data.get("installed") or {}
        client_id = web_config.get("client_id")
        client_secret = web_config.get("client_secret")
        if client_id and client_secret:
            return client_id, client_secret

    raise CalendarConfigurationError(
        "Google OAuth is not configured. Set GOOGLE_OAUTH_CLIENT_ID and "
        "GOOGLE_OAUTH_CLIENT_SECRET, or GOOGLE_OAUTH_CLIENT_SECRETS_FILE."
    )


def _fetch_google_email(credentials: Credentials) -> str | None:
    try:
        response = AuthorizedSession(credentials).get(USERINFO_URL, timeout=10)
        if not response.ok:
            return None
        data = response.json()
        return data.get("email")
    except Exception:
        return None


def _normalize_expiry(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value

