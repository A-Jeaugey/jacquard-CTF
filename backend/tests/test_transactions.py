"""Les écritures doivent être validées avant que la réponse ne parte vers le client."""

import asyncio
from typing import Any

from sqlalchemy import select

from jacquard.db import get_sessionmaker
from jacquard.main import create_app
from jacquard.models import AuthSession, User


def test_commit_happens_before_response_is_sent(sync) -> None:  # type: ignore[no-untyped-def]
    sync()
    app = create_app()
    body = b'{"username": "alice", "password": "motdepasse-solide"}'
    scope: dict[str, Any] = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/auth/register",
        "raw_path": b"/api/auth/register",
        "query_string": b"",
        "root_path": "",
        "headers": [
            (b"host", b"testserver"),
            (b"content-type", b"application/json"),
            (b"cookie", b"jq_csrf=jeton"),
            (b"x-csrf-token", b"jeton"),
        ],
        "client": ("127.0.0.1", 1234),
        "server": ("testserver", 80),
    }
    seen_at_response_start: dict[str, Any] = {}
    request_sent = False

    async def receive() -> dict[str, Any]:
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        await asyncio.sleep(3600)
        return {"type": "http.disconnect"}  # pragma: no cover

    async def send(message: dict[str, Any]) -> None:
        if message["type"] == "http.response.start":
            seen_at_response_start["status"] = message["status"]
            # Une autre connexion doit déjà voir l'utilisateur et sa session.
            with get_sessionmaker()() as db:
                user = db.scalar(select(User).where(User.username_key == "alice"))
                seen_at_response_start["user"] = user is not None
                seen_at_response_start["sessions"] = (
                    len(list(db.scalars(select(AuthSession).where(AuthSession.user_id == user.id))))
                    if user
                    else 0
                )

    asyncio.run(app(scope, receive, send))
    assert seen_at_response_start == {"status": 201, "user": True, "sessions": 1}
