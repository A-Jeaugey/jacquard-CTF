from datetime import timedelta


def _team(new_client, name: str):  # type: ignore[no-untyped-def]
    api = new_client()
    api.register(name.lower())
    api.create_team(name)
    return api


def test_stats_per_challenge(new_client, sync, admin, clock) -> None:  # type: ignore[no-untyped-def]
    sync()
    alpha, bravo, charlie = (_team(new_client, n) for n in ("Alpha", "Bravo", "Charlie"))
    for team in (alpha, bravo, charlie):
        team.submit("cesar", "DEMO{jules_cesar_etait_la}")  # même erreur, 3 équipes
    alpha.post("/api/challenges/cesar/hints/cesar-1/unlock")
    clock.set(clock.now + timedelta(minutes=10))
    alpha.submit("cesar", "DEMO{jules_serait_fier}")
    bravo.submit("cesar", "DEMO{jules_serait_fier}")

    stats = admin.get("/api/admin/stats").json()
    cesar = next(c for c in stats["challenges"] if c["id"] == "cesar")
    assert cesar["solves"] == 2
    assert cesar["attempts"] == 5
    assert cesar["wrong"] == 3
    assert cesar["hints"] == 1
    assert cesar["top_wrong"] == [{"value": "DEMO{jules_cesar_etait_la}", "count": 3}]
    assert cesar["first_solve_minutes"] == cesar["median_solve_minutes"]

    kinds = {s["kind"] for s in stats["signals"]}
    assert "same_wrong_answer" in kinds
    assert "shared_ip" in kinds  # les clients de test partagent la même adresse


def test_stats_burst_signal(new_client, sync, admin) -> None:  # type: ignore[no-untyped-def]
    sync()
    speedy = _team(new_client, "Speedy")
    for challenge, flag in (
        ("bienvenue", "DEMO{bienvenue_a_bord}"),
        ("cesar", "DEMO{jules_serait_fier}"),
        ("couches", "DEMO{trois_couches_suffisent}"),
        ("ville", "DEMO{lyon}"),
    ):
        speedy.submit(challenge, flag)
    signals = admin.get("/api/admin/stats").json()["signals"]
    assert any(s["kind"] == "burst" and s["team"] == "Speedy" for s in signals)


def test_stats_requires_admin(player) -> None:  # type: ignore[no-untyped-def]
    assert player.get("/api/admin/stats").status_code == 403
