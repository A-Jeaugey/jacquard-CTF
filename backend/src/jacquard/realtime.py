"""Diffusion d'événements en temps réel (Server-Sent Events).

Les événements sont publiés avec `pg_notify` dans la transaction de la requête : ils ne
partent qu'au commit, et jamais si la requête échoue. Chaque processus serveur écoute le
canal PostgreSQL avec une seule connexion et redistribue aux navigateurs connectés.
Aucun service supplémentaire (Redis...) n'est nécessaire, même avec plusieurs workers.
"""

import asyncio
import contextlib
import json
import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

import psycopg
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

CHANNEL = "jacquard_events"
QUEUE_SIZE = 100

log = logging.getLogger(__name__)


def publish(
    session: Session,
    kind: str,
    data: dict[str, Any],
    *,
    public: bool = False,
    teams: Iterable[int] = (),
    admin: bool = True,
) -> None:
    """Publie un événement, envoyé au commit de la session.

    `public` : tous les visiteurs ; `teams` : membres de ces équipes ; `admin` : orga.
    """
    payload = json.dumps(
        {
            "type": kind,
            "data": data,
            "audience": {"public": public, "teams": sorted(set(teams)), "admin": admin},
        },
        separators=(",", ":"),
        ensure_ascii=False,
    )
    session.execute(select(func.pg_notify(CHANNEL, payload)))


@dataclass(eq=False)
class Subscriber:
    team_id: int | None
    is_admin: bool
    queue: asyncio.Queue[dict[str, Any]] = field(
        default_factory=lambda: asyncio.Queue(maxsize=QUEUE_SIZE)
    )

    def wants(self, audience: dict[str, Any]) -> bool:
        if audience.get("public"):
            return True
        if self.is_admin and audience.get("admin"):
            return True
        return self.team_id is not None and self.team_id in audience.get("teams", [])


class Broker:
    def __init__(self) -> None:
        self.subscribers: set[Subscriber] = set()
        self._task: asyncio.Task[None] | None = None
        self.listening = asyncio.Event()

    def subscribe(self, team_id: int | None, is_admin: bool) -> Subscriber:
        subscriber = Subscriber(team_id=team_id, is_admin=is_admin)
        self.subscribers.add(subscriber)
        return subscriber

    def unsubscribe(self, subscriber: Subscriber) -> None:
        self.subscribers.discard(subscriber)

    def dispatch(self, message: dict[str, Any]) -> None:
        audience = message.get("audience", {})
        event = {"type": message["type"], "data": message["data"]}
        for subscriber in list(self.subscribers):
            if not subscriber.wants(audience):
                continue
            if subscriber.queue.full():
                # Client trop lent : on jette le plus ancien, il se resynchronisera.
                with contextlib.suppress(asyncio.QueueEmpty):
                    subscriber.queue.get_nowait()
            subscriber.queue.put_nowait(event)

    def start(self, database_url: str) -> None:
        url = make_url(database_url).set(drivername="postgresql")
        dsn = url.render_as_string(hide_password=False)
        self._task = asyncio.create_task(self._listen(dsn))

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def _listen(self, dsn: str) -> None:
        delay = 1.0
        while True:
            try:
                async with await psycopg.AsyncConnection.connect(dsn, autocommit=True) as conn:
                    await conn.execute(f"LISTEN {CHANNEL}")
                    self.listening.set()
                    delay = 1.0
                    async for notification in conn.notifies():
                        try:
                            self.dispatch(json.loads(notification.payload))
                        except (ValueError, KeyError):
                            log.warning("notification ignorée : %r", notification.payload)
            except asyncio.CancelledError:
                raise
            except Exception:  # pragma: no cover - dépend de la base
                self.listening.clear()
                log.exception(
                    "écoute temps réel interrompue, nouvelle tentative dans %.0f s", delay
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30.0)


broker = Broker()
