import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.event_store import WebhookEventStore, to_sse
from app.models import ChargeCreateInput, SimulateWebhookInput
from app.settings import Settings, get_settings
from app.webhook import simulated_webhook_payload, summarize_payload


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    project_root = Path(__file__).resolve().parent.parent
    static_dir = project_root / "static"

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = app_settings
        app.state.events = WebhookEventStore(limit=app_settings.webhook_event_limit)
        yield

    app = FastAPI(title="Hackthon Pix Test UI", version="0.1.0", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/api/config")
    async def read_config() -> dict[str, Any]:
        return {
            "pixApiBaseUrl": app_settings.pix_api_base_url,
            "webhookUrl": app_settings.webhook_url,
            "forwardWebhookToPixApi": app_settings.forward_webhook_to_pix_api,
        }

    @app.post("/api/charges", status_code=status.HTTP_201_CREATED)
    async def create_charge(payload: ChargeCreateInput) -> dict[str, Any]:
        request_payload = payload.to_pix_api_payload()
        try:
            response = await post_json_to_pix_api(
                app_settings,
                path="/charges",
                json_payload=request_payload,
            )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Falha ao chamar API Pix: {exc}",
            ) from exc

        if response.is_error:
            raise HTTPException(status_code=response.status_code, detail=parse_response(response))

        return parse_response(response)

    @app.get("/api/charges/{correlation_id}")
    async def read_charge(correlation_id: str) -> Any:
        try:
            async with httpx.AsyncClient(timeout=app_settings.request_timeout) as client:
                response = await client.get(
                    f"{app_settings.pix_api_base_url}/charges/{correlation_id}"
                )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Falha ao consultar API Pix: {exc}",
            ) from exc

        if response.is_error:
            raise HTTPException(status_code=response.status_code, detail=parse_response(response))
        return parse_response(response)

    @app.get("/api/webhook-events")
    async def list_webhook_events(request: Request) -> list[dict[str, Any]]:
        events: WebhookEventStore = request.app.state.events
        return await events.list()

    @app.delete("/api/webhook-events", status_code=status.HTTP_204_NO_CONTENT)
    async def clear_webhook_events(request: Request) -> Response:
        events: WebhookEventStore = request.app.state.events
        await events.clear()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.get("/api/webhook-events/stream")
    async def stream_webhook_events(request: Request) -> StreamingResponse:
        events: WebhookEventStore = request.app.state.events
        queue = await events.subscribe()

        async def event_generator() -> AsyncIterator[str]:
            try:
                yield "event: ready\ndata: {}\n\n"
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=15)
                        yield to_sse(event)
                    except TimeoutError:
                        yield ": keep-alive\n\n"
            finally:
                await events.unsubscribe(queue)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.post("/api/simulate-webhook", status_code=status.HTTP_202_ACCEPTED)
    async def simulate_webhook(payload: SimulateWebhookInput, request: Request) -> dict[str, Any]:
        webhook_payload = simulated_webhook_payload(
            correlation_id=payload.correlation_id,
            value=payload.value,
            status=payload.status,
            provider_charge_id=payload.provider_charge_id,
            payment_link_id=payload.payment_link_id,
        )
        return await handle_webhook_payload(
            request=request,
            raw_body=json.dumps(webhook_payload).encode("utf-8"),
            payload=webhook_payload,
            headers={"x-simulated-webhook": "true"},
            source="simulation",
        )

    @app.post("/webhooks/woovi")
    async def woovi_webhook(request: Request) -> dict[str, Any]:
        raw_body = await request.body()
        try:
            payload = json.loads(raw_body or b"{}")
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Payload JSON invalido") from exc

        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Payload deve ser um objeto JSON")

        headers = {
            key: value
            for key, value in request.headers.items()
            if key.lower() in {"authorization", "x-webhook-signature", "content-type"}
        }
        return await handle_webhook_payload(
            request=request,
            raw_body=raw_body,
            payload=payload,
            headers=headers,
            source="woovi",
        )

    return app


async def handle_webhook_payload(
    *,
    request: Request,
    raw_body: bytes,
    payload: dict[str, Any],
    headers: dict[str, str],
    source: str,
) -> dict[str, Any]:
    settings: Settings = request.app.state.settings
    events: WebhookEventStore = request.app.state.events
    summary = summarize_payload(payload)
    forward_result: dict[str, Any] | None = None

    if settings.forward_webhook_to_pix_api:
        try:
            forward_result = await forward_webhook(settings, raw_body=raw_body, headers=headers)
        except httpx.RequestError as exc:
            forward_result = {"ok": False, "error": str(exc)}

    event = await events.add(
        {
            "source": source,
            "summary": summary,
            "headers": safe_headers(headers),
            "payload": payload,
            "forward": forward_result,
        }
    )

    return {
        "ok": True,
        "eventID": event["id"],
        "summary": summary,
        "forward": forward_result,
    }


async def forward_webhook(
    settings: Settings,
    *,
    raw_body: bytes,
    headers: dict[str, str],
) -> dict[str, Any]:
    forward_headers = {
        key: value
        for key, value in headers.items()
        if key.lower() in {"authorization", "x-webhook-signature", "content-type"}
    }
    if "content-type" not in {key.lower() for key in forward_headers}:
        forward_headers["Content-Type"] = "application/json"

    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        response = await client.post(
            f"{settings.pix_api_base_url}/webhooks/woovi",
            content=raw_body,
            headers=forward_headers,
        )

    return {
        "ok": not response.is_error,
        "statusCode": response.status_code,
        "body": parse_response(response),
    }


async def post_json_to_pix_api(
    settings: Settings,
    *,
    path: str,
    json_payload: dict[str, Any],
) -> httpx.Response:
    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        return await client.post(
            f"{settings.pix_api_base_url}{path}",
            json=json_payload,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )


def parse_response(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text


def safe_headers(headers: dict[str, str]) -> dict[str, str]:
    safe = dict(headers)
    if "authorization" in safe:
        safe["authorization"] = mask(safe["authorization"])
    if "Authorization" in safe:
        safe["Authorization"] = mask(safe["Authorization"])
    return safe


def mask(value: str) -> str:
    if len(value) <= 8:
        return "********"
    return f"{value[:4]}...{value[-4:]}"


app = create_app()
