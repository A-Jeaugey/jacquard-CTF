"""Test de charge : simule des joueurs sur une instance Jacquard qui sert le pack de démo.

    cd backend
    uv run python ../scripts/load_test.py --url http://127.0.0.1:8000 --joueurs 150 --duree 120

Chaque joueur s'inscrit, crée ou rejoint une équipe (4 par équipe), garde son flux temps
réel ouvert, puis enchaîne au hasard : liste des défis, détail d'un défi, classement,
soumission de flags (bons ou mauvais). Le script affiche les temps de réponse par route.
"""

import argparse
import asyncio
import random
import statistics
import time
from collections import defaultdict

import httpx

DEMO_FLAGS = {
    "bienvenue": "DEMO{bienvenue_a_bord}",
    "cesar": "DEMO{jules_serait_fier}",
    "couches": "DEMO{trois_couches_suffisent}",
    "ville": "DEMO{lyon}",
}
EXPECTED = {200, 201, 204, 403, 409, 429}  # 403/409/429 : refus normaux (verrou, doublon, limite)


class Stats:
    def __init__(self) -> None:
        self.latencies: dict[str, list[float]] = defaultdict(list)
        self.errors: dict[str, int] = defaultdict(int)
        self.events = 0

    def record(self, name: str, started: float, status: int) -> None:
        self.latencies[name].append((time.perf_counter() - started) * 1000)
        if status not in EXPECTED:
            self.errors[f"{name} {status}"] += 1


async def call(client: httpx.AsyncClient, stats: Stats, name: str, method: str, url: str, **kw) -> httpx.Response | None:  # type: ignore[no-untyped-def]
    started = time.perf_counter()
    try:
        response = await client.request(method, url, **kw)
    except httpx.HTTPError as error:
        stats.errors[f"{name} {type(error).__name__}"] += 1
        return None
    stats.record(name, started, response.status_code)
    return response


async def listen(client: httpx.AsyncClient, stats: Stats, stop: asyncio.Event) -> None:
    try:
        async with client.stream("GET", "/api/live", timeout=None) as response:
            async for line in response.aiter_lines():
                if line.startswith("event: "):
                    stats.events += 1
                if stop.is_set():
                    break
    except httpx.HTTPError:
        stats.errors["live déconnecté"] += 1


async def player(index: int, args: argparse.Namespace, stats: Stats, codes: dict[int, str], ready: asyncio.Event, stop: asyncio.Event) -> None:
    async with httpx.AsyncClient(base_url=args.url, timeout=30) as client:
        await call(client, stats, "GET /api/health", "GET", "/api/health")
        csrf = {"X-CSRF-Token": client.cookies.get("jq_csrf", "")}
        name = f"charge{args.run}{index}"
        await call(client, stats, "POST /api/auth/register", "POST", "/api/auth/register",
                   json={"username": name, "password": "motdepasse-solide"}, headers=csrf)  # fmt: skip
        team = index // 4
        if index % 4 == 0:
            response = await call(client, stats, "POST /api/teams", "POST", "/api/teams",
                                  json={"name": f"Équipe {args.run}-{team}"}, headers=csrf)  # fmt: skip
            if response is not None and response.status_code == 201:
                codes[team] = response.json()["invite_code"]
        else:
            for _ in range(100):
                if team in codes:
                    break
                await asyncio.sleep(0.1)
            await call(client, stats, "POST /api/teams/join", "POST", "/api/teams/join",
                       json={"invite_code": codes.get(team, "")}, headers=csrf)  # fmt: skip
        await ready.wait()
        listener = asyncio.create_task(listen(client, stats, stop))
        rng = random.Random(index)
        while not stop.is_set():
            await asyncio.sleep(rng.uniform(3, 12))
            roll = rng.random()
            if roll < 0.5:
                await call(client, stats, "GET /api/challenges", "GET", "/api/challenges")
            elif roll < 0.65:
                await call(client, stats, "GET /api/challenges/{id}", "GET", f"/api/challenges/{rng.choice(list(DEMO_FLAGS))}")
            elif roll < 0.85:
                await call(client, stats, "GET /api/scoreboard", "GET", "/api/scoreboard")
            else:
                challenge = rng.choice(list(DEMO_FLAGS))
                flag = DEMO_FLAGS[challenge] if rng.random() < 0.3 else f"DEMO{{essai_{rng.randrange(10**6)}}}"
                await call(client, stats, "POST submit", "POST", f"/api/challenges/{challenge}/submit",
                           json={"flag": flag}, headers=csrf)  # fmt: skip
        listener.cancel()


async def main(args: argparse.Namespace) -> None:
    stats, codes = Stats(), {}
    ready, stop = asyncio.Event(), asyncio.Event()
    tasks = [asyncio.create_task(player(i, args, stats, codes, ready, stop)) for i in range(args.joueurs)]
    await asyncio.sleep(min(30, 2 + args.joueurs / 20))  # le temps des inscriptions
    print(f"{args.joueurs} joueurs inscrits, {len(codes)} équipes ; charge pendant {args.duree} s…")
    ready.set()
    started = time.perf_counter()
    await asyncio.sleep(args.duree)
    stop.set()
    await asyncio.wait(tasks, timeout=20)
    elapsed = time.perf_counter() - started

    total = sum(len(v) for v in stats.latencies.values())
    print(f"\n{total} requêtes en {elapsed:.0f} s ({total / elapsed:.1f} req/s), {stats.events} événements temps réel reçus\n")
    print(f"{'route':<28}{'n':>6}{'médiane':>10}{'p95':>9}{'p99':>9}{'max':>9}  (ms)")
    for name, values in sorted(stats.latencies.items()):
        values.sort()
        pick = lambda q: values[min(len(values) - 1, int(q * len(values)))]  # noqa: E731
        print(f"{name:<28}{len(values):>6}{statistics.median(values):>10.0f}{pick(0.95):>9.0f}{pick(0.99):>9.0f}{values[-1]:>9.0f}")
    print("\nErreurs :", dict(stats.errors) or "aucune")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--joueurs", type=int, default=150)
    parser.add_argument("--duree", type=int, default=120, help="durée de la phase de jeu, en secondes")
    parser.add_argument("--run", default=str(int(time.time()) % 10000), help="suffixe des pseudos")
    asyncio.run(main(parser.parse_args()))
