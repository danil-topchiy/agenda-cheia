from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.dependencies import get_database
from app.oauth import (
    create_authorization_url,
    handle_oauth_callback,
    list_oauth_connection_responses,
    oauth_connection_to_response,
)
from app.repository import delete_oauth_connection, get_oauth_connection
from app.schemas import OAuthCallbackResponse, OAuthConnectionResponse, OAuthLoginResponse
from app.settings import Settings, get_settings

router = APIRouter(prefix="/auth/google", tags=["google-oauth"])


@router.get("/login", response_model=OAuthLoginResponse)
def google_oauth_login(
    user_id: str = Query(..., min_length=1),
    calendar_id: str = Query(default="primary", min_length=1),
    redirect_after: str | None = None,
    redirect: bool = False,
    db: Session = Depends(get_database),
    settings: Settings = Depends(get_settings),
):
    authorization_url, state = create_authorization_url(
        db,
        settings,
        user_id=user_id,
        calendar_id=calendar_id,
        redirect_after=redirect_after,
    )
    if redirect:
        return RedirectResponse(authorization_url)
    return OAuthLoginResponse(
        authorization_url=authorization_url,
        state=state,
        user_id=user_id,
        calendar_id=calendar_id,
    )


@router.get("/callback", response_model=OAuthCallbackResponse)
def google_oauth_callback(
    request: Request,
    state: str,
    db: Session = Depends(get_database),
    settings: Settings = Depends(get_settings),
) -> OAuthCallbackResponse:
    connection = handle_oauth_callback(
        db,
        settings,
        state=state,
        authorization_response=str(request.url),
    )
    return OAuthCallbackResponse(
        connected=True,
        connection=oauth_connection_to_response(connection),
    )


@router.get("/connections", response_model=list[OAuthConnectionResponse])
def google_oauth_connections(db: Session = Depends(get_database)) -> list[OAuthConnectionResponse]:
    return list_oauth_connection_responses(db)


@router.get("/connections/{user_id}", response_model=OAuthConnectionResponse)
def google_oauth_connection(
    user_id: str,
    db: Session = Depends(get_database),
) -> OAuthConnectionResponse:
    connection = get_oauth_connection(db, user_id)
    if connection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Google OAuth connection not found")
    return oauth_connection_to_response(connection)


@router.delete("/connections/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def google_oauth_disconnect(
    user_id: str,
    db: Session = Depends(get_database),
) -> None:
    deleted = delete_oauth_connection(db, user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Google OAuth connection not found")
    db.commit()

