"""Temps réel : audience des événements et flux SSE de bout en bout."""

import json
import queue
import socket
import threading
import time
from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import httpx
import psycopg
import pytest
import uvicorn
from sqlalchemy.engine import make_url

from jacquard.config import get_settings
from jacquard.realtime import CHANNEL, Subscriber, broker

# --------------------------------------------------------------------------- audience


def test_subscriber_filtering() -> None:
    player = Subscriber(team_id=1, is_admin=False)
    other = Subscriber(team_id=2, is_admin=False)
    orga = Subscriber(team_id=None, is_admin=True)
    anonymous = Subscriber(team_id=None, is_admin=False)

    public = {"public": True, "teams": [], "admin": True}
    team_only = {"public": False, "teams": [1], "admin": False}
    team_and_admin = {"public": False, "teams": [1], "admin": True}

    assert all(s.wants(public) for s in (player, other, orga, anonymous))
    assert [s.wants(team_only) for s in (player, other, orga, anonymous)] == [
        True,
        False,
        False,
        False,
    ]
    assert [s.wants(team_and_admin) for s in (player, other, orga, anonymous)] == [
        True,
        False,
        True,
        False,
    ]


def test_slow_client_drops_oldest_event() -> None:
    subscriber = broker.subscribe(team_id=None, is_admin=False)
    try:
        for i in range(150):
            broker.dispatch({"type": "t", "data": {"i": i}, "audience": {"public": True}})
        assert subscriber.queue.qsize() == 100
        assert subscriber.queue.get_nowait()["data"]["i"] == 50
    finally:
        broker.unsubscribe(subscriber)


def _psycopg_dsn() -> str:
    url = make_url(get_settings().database_url).set(drivername="postgresql")
    return url.render_as_string(hide_password=False)


def test_events_are_published_on_commit(player) -> None:  # type: ignore[no-untyped-def]
    team_id = player.get("/api/teams/me").json()["id"]
    with psycopg.connect(_psycopg_dsn(), autocommit=True) as conn:
        conn.execute(f"LISTEN {CHANNEL}")
        player.submit("cesar", "DEMO{faux}")
        player.submit("cesar", "DEMO{jules_serait_fier}")
        player.submit("couches", "DEMO{trois_couches_suffisent}")
        events = [json.loads(n.payload) for n in conn.notifies(timeout=0.5, stop_after=10)]

    kinds = [e["type"] for e in events]
    assert kinds == ["solve", "team_update", "solve", "team_update", "unlock"]
    solve = events[0]
    assert solve["data"] == {
        "team_id": team_id,
        "team": "Les Testeurs",
        "challenge_id": "cesar",
        "challenge": "Ave César",
        "first_blood": 1,
    }
    assert solve["audience"] == {"public": True, "teams": [team_id], "admin": True}
    assert events[1]["audience"] == {"public": False, "teams": [team_id], "admin": False}
    assert events[4]["data"]["challenges"] == [{"id": "avance", "name": "Niveau supérieur"}]
    assert events[4]["audience"]["public"] is False


def test_frozen_solves_are_not_public(new_client, sync, make_pack, clock) -> None:  # type: ignore[no-untyped-def]
    sync(
        make_pack(
            schedule={
                "start": "2027-06-01T10:00:00",
                "end": "2027-06-01T18:00:00",
                "freeze": "2027-06-01T13:00:00",
            }
        )
    )
    api = new_client()
    api.register("alice")
    api.create_team("Alpha")
    clock.set(clock.now + timedelta(hours=1))
    with psycopg.connect(_psycopg_dsn(), autocommit=True) as conn:
        conn.execute(f"LISTEN {CHANNEL}")
        api.submit("ville", "DEMO{lyon}")
        events = [json.loads(n.payload) for n in conn.notifies(timeout=0.5, stop_after=10)]
    solve = next(e for e in events if e["type"] == "solve")
    assert solve["audience"]["public"] is False
    assert solve["audience"]["admin"] is True


def test_hidden_team_solves_are_not_public(player, admin) -> None:  # type: ignore[no-untyped-def]
    team_id = player.get("/api/teams/me").json()["id"]
    admin.patch(f"/api/admin/teams/{team_id}", {"hidden": True})
    with psycopg.connect(_psycopg_dsn(), autocommit=True) as conn:
        conn.execute(f"LISTEN {CHANNEL}")
        result = player.submit("ville", "DEMO{lyon}").json()
        events = [json.loads(n.payload) for n in conn.notifies(timeout=0.5, stop_after=10)]
    assert result["first_blood"] is None
    solve = next(e for e in events if e["type"] == "solve")
    assert solve["audience"]["public"] is False


# --------------------------------------------------------------------------- flux SSE réel


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture
def server(sync) -> Iterator[str]:  # type: ignore[no-untyped-def]
    from jacquard.main import create_app

    sync()
    port = _free_port()
    config = uvicorn.Config(
        create_app(), host="127.0.0.1", port=port, log_level="warning", timeout_graceful_shutdown=1
    )
    instance = uvicorn.Server(config)
    thread = threading.Thread(target=instance.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not (instance.started and broker.listening.is_set()):
        if time.monotonic() > deadline:
            raise RuntimeError("le serveur de test n'a pas démarré")
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    instance.should_exit = True
    thread.join(timeout=10)


def _http_player(base: str, username: str, team: str) -> httpx.Client:
    client = httpx.Client(base_url=base, timeout=5)
    client.get("/api/health")
    headers = {"X-CSRF-Token": client.cookies["jq_csrf"]}
    client.post(
        "/api/auth/register",
        json={"username": username, "password": "motdepasse-solide"},
        headers=headers,
    ).raise_for_status()
    client.post("/api/teams", json={"name": team}, headers=headers).raise_for_status()
    return client


def _listen(
    client: httpx.Client, out: "queue.Queue[tuple[str, Any]]", ready: threading.Event
) -> None:
    with client.stream("GET", "/api/live", timeout=httpx.Timeout(5, read=20)) as response:
        kind = None
        for line in response.iter_lines():
            if line.startswith("retry:"):
                ready.set()
            elif line.startswith("event: "):
                kind = line.removeprefix("event: ")
            elif line.startswith("data: ") and kind:
                out.put((kind, json.loads(line.removeprefix("data: "))))
                if kind == "unlock":
                    return


def test_live_stream_end_to_end(server: str) -> None:
    alice = _http_player(server, "alice", "Alpha")
    bob = _http_player(server, "bob", "Bravo")
    alice_events: queue.Queue[tuple[str, Any]] = queue.Queue()
    bob_events: queue.Queue[tuple[str, Any]] = queue.Queue()
    ready_a, ready_b = threading.Event(), threading.Event()
    listeners = [
        threading.Thread(target=_listen, args=(alice, alice_events, ready_a), daemon=True),
        threading.Thread(target=_listen, args=(bob, bob_events, ready_b), daemon=True),
    ]
    for listener in listeners:
        listener.start()
    assert ready_a.wait(5) and ready_b.wait(5)
    time.sleep(0.2)  # laisse le temps aux abonnements d'être enregistrés

    headers = {"X-CSRF-Token": alice.cookies["jq_csrf"]}
    for challenge, flag in (
        ("cesar", "DEMO{jules_serait_fier}"),
        ("couches", "DEMO{trois_couches_suffisent}"),
    ):
        alice.post(f"/api/challenges/{challenge}/submit", json={"flag": flag}, headers=headers)

    received_by_alice = []
    while True:
        kind, data = alice_events.get(timeout=5)
        received_by_alice.append(kind)
        if kind == "unlock":
            assert data["challenges"] == [{"id": "avance", "name": "Niveau supérieur"}]
            break
    assert received_by_alice == ["solve", "team_update", "solve", "team_update", "unlock"]

    # Bob voit les résolutions publiques, mais rien de ce qui est propre à l'équipe d'Alice.
    received_by_bob = []
    for _ in range(2):
        received_by_bob.append(bob_events.get(timeout=5))
    assert [k for k, _ in received_by_bob] == ["solve", "solve"]
    assert received_by_bob[0][1]["first_blood"] == 1
    time.sleep(0.3)
    assert bob_events.empty()

    alice.close()
    bob.close()


def test_announcements_are_published(admin) -> None:  # type: ignore[no-untyped-def]
    with psycopg.connect(_psycopg_dsn(), autocommit=True) as conn:
        conn.execute(f"LISTEN {CHANNEL}")
        admin.post("/api/admin/announcements", {"title": "Pause pizza", "body": "🍕"})
        events = [json.loads(n.payload) for n in conn.notifies(timeout=0.5, stop_after=5)]
    assert events[0]["type"] == "announcement"
    assert events[0]["data"]["title"] == "Pause pizza"
    assert events[0]["audience"]["public"] is True
