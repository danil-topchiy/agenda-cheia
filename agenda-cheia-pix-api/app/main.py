import hmac
import json
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request, Response, status

from app.config import Settings, get_settings
from app.database import (
    get_charge,
    init_db,
    save_webhook_event,
    upsert_charge_from_provider,
)
from app.schemas import ChargeCreateRequest, ChargeRecord, ChargeResponse
from app.webhook_security import WebhookSignatureError, WebhookSignatureVerifier
from app.woovi_client import MissingWooviAppIDError, WooviAPIError, WooviClient


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_db(app_settings)
        app.state.settings = app_settings
        app.state.woovi_client = WooviClient(app_settings)
        app.state.webhook_verifier = WebhookSignatureVerifier(app_settings)
        yield

    app = FastAPI(
        title="Agenda Cheia Pix API",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(
        "/charges",
        response_model=ChargeResponse,
        response_model_by_alias=True,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_charge(charge_request: ChargeCreateRequest, request: Request) -> dict[str, Any]:
        payload = charge_request.to_woovi_payload()
        woovi_client: WooviClient = request.app.state.woovi_client

        try:
            provider_response = await woovi_client.create_charge(payload)
        except MissingWooviAppIDError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except WooviAPIError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

        saved = upsert_charge_from_provider(
            app_settings,
            request_payload=payload,
            provider_response=provider_response,
        )

        return normalize_charge_response(saved, provider_response)

    @app.get(
        "/charges/{correlation_id}",
        response_model=ChargeRecord,
        response_model_by_alias=True,
    )
    async def read_charge(correlation_id: str) -> dict[str, Any]:
        charge = get_charge(app_settings, correlation_id)
        if not charge:
            raise HTTPException(status_code=404, detail="Cobranca nao encontrada")
        return charge

    @app.post("/webhooks/woovi", status_code=status.HTTP_200_OK)
    async def woovi_webhook(
        request: Request,
        authorization: str | None = Header(default=None),
        x_webhook_signature: str | None = Header(default=None),
    ) -> Response:
        raw_body = await request.body()
        validate_webhook_authorization(app_settings, authorization)

        if app_settings.woovi_webhook_verify_signature:
            verifier: WebhookSignatureVerifier = request.app.state.webhook_verifier
            try:
                await verifier.verify(raw_body, x_webhook_signature)
            except WebhookSignatureError as exc:
                raise HTTPException(status_code=401, detail=str(exc)) from exc

        try:
            payload = json.loads(raw_body or b"{}")
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Payload JSON invalido") from exc

        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Payload deve ser um objeto JSON")

        save_webhook_event(app_settings, payload)

        return Response(status_code=status.HTTP_200_OK)

    return app


def validate_webhook_authorization(
    settings: Settings, received_authorization: str | None
) -> None:
    expected = settings.woovi_webhook_authorization
    if not expected:
        return

    if not received_authorization or not hmac.compare_digest(
        received_authorization, expected
    ):
        raise HTTPException(status_code=401, detail="Webhook nao autorizado")


def normalize_charge_response(
    saved: dict[str, Any], provider_response: dict[str, Any]
) -> dict[str, Any]:
    return {
        "correlationID": saved.get("correlation_id"),
        "value": saved.get("value"),
        "status": saved.get("status"),
        "expiresIn": saved.get("expires_in"),
        "expiresDate": saved.get("expires_date"),
        "brCode": saved.get("br_code"),
        "qrCodeImage": saved.get("qr_code_image"),
        "paymentLinkUrl": saved.get("payment_link_url"),
        "providerChargeID": saved.get("provider_charge_id"),
        "raw": provider_response,
    }


app = create_app()
