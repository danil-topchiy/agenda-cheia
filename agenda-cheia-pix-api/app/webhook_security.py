import base64
import time
from typing import Any

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from app.config import Settings


class WebhookSignatureError(Exception):
    pass


class WebhookSignatureVerifier:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._public_keys: list[str] = []
        self._expires_at = 0.0

    async def verify(self, raw_body: bytes, signature: str | None) -> bool:
        if not signature:
            raise WebhookSignatureError("Header x-webhook-signature ausente")

        try:
            decoded_signature = base64.b64decode(signature, validate=True)
        except ValueError as exc:
            raise WebhookSignatureError("Assinatura nao esta em Base64 valido") from exc

        public_keys = await self.get_public_keys()
        for key_pem in public_keys:
            if verify_with_key(key_pem, raw_body, decoded_signature):
                return True

        raise WebhookSignatureError("Assinatura invalida")

    async def get_public_keys(self) -> list[str]:
        if self._public_keys and time.time() < self._expires_at:
            return self._public_keys

        try:
            async with httpx.AsyncClient(timeout=self.settings.woovi_request_timeout) as client:
                response = await client.get(self.settings.webhook_public_keys_url)
                response.raise_for_status()
                data = response.json()
        except Exception as exc:
            if self._public_keys:
                return self._public_keys
            raise WebhookSignatureError("Falha ao buscar chaves publicas da Woovi") from exc

        keys = extract_public_keys(data)
        if not keys:
            raise WebhookSignatureError("Nenhuma chave publica retornada pela Woovi")

        self._public_keys = keys
        self._expires_at = time.time() + cache_ttl_seconds(response.headers.get("cache-control"))
        return self._public_keys


def extract_public_keys(data: dict[str, Any]) -> list[str]:
    entries = data.get("public_keys")
    if not isinstance(entries, list):
        return []

    keys = []
    for entry in entries:
        if isinstance(entry, dict) and isinstance(entry.get("key"), str):
            keys.append(entry["key"])
    return keys


def verify_with_key(key_pem: str, raw_body: bytes, signature: bytes) -> bool:
    try:
        public_key = serialization.load_pem_public_key(key_pem.encode("utf-8"))
        public_key.verify(signature, raw_body, padding.PKCS1v15(), hashes.SHA256())
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False


def cache_ttl_seconds(cache_control: str | None) -> int:
    if not cache_control:
        return 3600

    for part in cache_control.split(","):
        part = part.strip().lower()
        if part.startswith("max-age="):
            try:
                return max(1, int(part.split("=", 1)[1]))
            except ValueError:
                return 3600
    return 3600

