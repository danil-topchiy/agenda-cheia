from typing import Any

import httpx

from app.config import Settings


class WooviAPIError(Exception):
    def __init__(self, status_code: int, detail: Any):
        super().__init__(str(detail))
        self.status_code = status_code
        self.detail = detail


class MissingWooviAppIDError(Exception):
    pass


class WooviClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def create_charge(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = self.auth_headers()

        async with httpx.AsyncClient(timeout=self.settings.woovi_request_timeout) as client:
            response = await client.post(
                self.settings.charge_url,
                headers=headers,
                json=payload,
            )

        return parse_success_response(response)

    async def create_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = self.auth_headers()

        async with httpx.AsyncClient(timeout=self.settings.woovi_request_timeout) as client:
            response = await client.post(
                self.settings.webhook_url,
                headers=headers,
                json=payload,
            )

        return parse_success_response(response)

    def auth_headers(self) -> dict[str, str]:
        if not self.settings.woovi_app_id:
            raise MissingWooviAppIDError("WOOVI_APP_ID nao configurado")

        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": self.settings.woovi_app_id,
        }


def parse_error_response(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text


def parse_success_response(response: httpx.Response) -> dict[str, Any]:
    if response.is_error:
        raise WooviAPIError(response.status_code, parse_error_response(response))

    try:
        data = response.json()
    except ValueError as exc:
        raise WooviAPIError(502, "Resposta invalida da Woovi") from exc

    if not isinstance(data, dict):
        raise WooviAPIError(502, "Resposta inesperada da Woovi")

    return data
