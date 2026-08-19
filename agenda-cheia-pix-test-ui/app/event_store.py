import asyncio
import json
from collections import deque
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class WebhookEventStore:
    def __init__(self, limit: int = 200):
        self.limit = limit
        self._events: deque[dict[str, Any]] = deque(maxlen=limit)
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._lock = asyncio.Lock()

    async def add(self, event: dict[str, Any]) -> dict[str, Any]:
        event = {
            "id": event.get("id") or str(uuid4()),
            "receivedAt": event.get("receivedAt") or utc_now(),
            **event,
        }
        async with self._lock:
            self._events.appendleft(event)
            subscribers = list(self._subscribers)

        for queue in subscribers:
            queue.put_nowait(event)
        return event

    async def list(self) -> list[dict[str, Any]]:
        async with self._lock:
            return list(self._events)

    async def clear(self) -> None:
        async with self._lock:
            self._events.clear()

    async def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        async with self._lock:
            self._subscribers.add(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        async with self._lock:
            self._subscribers.discard(queue)


def to_sse(event: dict[str, Any]) -> str:
    return f"event: webhook\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"

