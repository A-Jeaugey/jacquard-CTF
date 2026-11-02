"""Flux d'événements en temps réel (Server-Sent Events)."""

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from jacquard.api.deps import SESSION_COOKIE
from jacquard.clock import utcnow
from jacquard.db import get_sessionmaker
from jacquard.models import AuthSession, User
from jacquard.realtime import broker
from jacquard.security import token_digest

router = APIRouter(prefix="/api", tags=["live"])

KEEPALIVE_SECONDS = 15


def _identify(token: str | None) -> tuple[int | None, bool]:
    """Équipe et rôle du visiteur. Session ouverte puis refermée immédiatement : on ne
    garde pas de connexion à la base pendant toute la durée du flux."""
    if not token:
        return None, False
    with get_sessionmaker()() as db:
        auth = db.get(AuthSession, token_digest(token))
        if auth is None or auth.expires_at <= utcnow():
            return None, False
        user = db.get(User, auth.user_id)
        return (user.team_id, user.is_admin) if user else (None, False)


@router.get("/live")
async def live(request: Request) -> StreamingResponse:
    team_id, is_admin = await asyncio.to_thread(_identify, request.cookies.get(SESSION_COOKIE))
    subscriber = broker.subscribe(team_id, is_admin)

    async def stream() -> AsyncIterator[str]:
        try:
            yield "retry: 5000\n\n"
            while not await request.is_disconnected():
                try:
                    event = await asyncio.wait_for(subscriber.queue.get(), KEEPALIVE_SECONDS)
                except TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                data = json.dumps(event["data"], ensure_ascii=False)
                yield f"event: {event['type']}\ndata: {data}\n\n"
        finally:
            broker.unsubscribe(subscriber)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
