from datetime import UTC, datetime, timedelta

FREEZE_PACK = {
    "schedule": {
        "start": "2027-06-01T10:00:00",
        "end": "2027-06-01T18:00:00",
        "freeze": "2027-06-01T17:00:00",
    }
}
# 17:00 Europe/Paris en été = 15:00 UTC.
FREEZE = datetime(2027, 6, 1, 15, 0, tzinfo=UTC)


def _two_teams(new_client):  # type: ignore[no-untyped-def]
    alice = new_client()
    alice.register("alice")
    alice.create_team("Alpha")
    bob = new_client()
    bob.register("bob")
    bob.create_team("Bravo")
    return alice, bob


def test_scoreboard_ranks_teams(new_client, sync) -> None:  # type: ignore[no-untyped-def]
    sync()
    alice, bob = _two_teams(new_client)
    bob.submit("ville", "DEMO{lyon}")
    alice.submit("bienvenue", "DEMO{bienvenue_a_bord}")
    board = new_client().get("/api/scoreboard").json()
    assert board["frozen"] is False
    assert [(t["rank"], t["name"], t["score"]) for t in board["teams"]] == [
        (1, "Bravo", 80),
        (2, "Alpha", 40),
    ]
    # Le nombre de défis publics (pour dessiner les façades) ne compte pas « Le coffre », caché
    # tant qu'il est verrouillé ; « Niveau supérieur », montré verrouillé, est compté.
    assert board["challenges"] == 5
    # Même silhouette pour toutes les équipes : quartiers dans l'ordre de l'événement, une
    # fenêtre par défi public ; chaque équipe dit lesquelles sont allumées.
    assert [d["category"] for d in board["districts"]] == ["misc", "crypto", "osint"]
    assert sum(d["count"] for d in board["districts"]) == 5
    lit = {t["name"]: t["lit"] for t in board["teams"]}
    assert len(lit["Bravo"]) == 1 and len(lit["Alpha"]) == 1
    assert lit["Bravo"] != lit["Alpha"]


def test_freeze_hides_late_solves(new_client, sync, make_pack, clock, admin) -> None:  # type: ignore[no-untyped-def]
    sync(make_pack(**FREEZE_PACK))
    alice, bob = _two_teams(new_client)

    clock.set(FREEZE - timedelta(minutes=5))
    alice.submit("bienvenue", "DEMO{bienvenue_a_bord}")
    clock.set(FREEZE + timedelta(minutes=5))
    bob.submit("ville", "DEMO{lyon}")
    bob.submit("bienvenue", "DEMO{bienvenue_a_bord}")

    public = new_client().get("/api/scoreboard").json()
    assert public["frozen"] is True
    assert [(t["name"], t["score"]) for t in public["teams"]] == [("Alpha", 40), ("Bravo", 0)]

    # Les autres équipes ne voient pas les résolutions après le gel, même via les défis.
    listing = {c["id"]: c for c in alice.get("/api/challenges").json()["challenges"]}
    assert listing["ville"]["solves"] == 0

    # Chaque équipe voit son propre score réel.
    assert bob.get("/api/teams/me").json()["score"] == 80 + 30

    full = admin.get("/api/scoreboard").json()
    assert full["frozen"] is False
    assert [(t["name"], t["score"]) for t in full["teams"]] == [("Bravo", 110), ("Alpha", 40)]


def test_hidden_team_excluded(new_client, sync, admin) -> None:  # type: ignore[no-untyped-def]
    sync()
    alice, bob = _two_teams(new_client)
    alpha_id = alice.get("/api/teams/me").json()["id"]
    assert admin.patch(f"/api/admin/teams/{alpha_id}", {"hidden": True}).status_code == 200
    alice.submit("bienvenue", "DEMO{bienvenue_a_bord}")
    bob.submit("bienvenue", "DEMO{bienvenue_a_bord}")
    board = new_client().get("/api/scoreboard").json()
    assert [t["name"] for t in board["teams"]] == ["Bravo"]
    # Bravo récupère le premier sang puisque l'équipe masquée ne compte pas.
    assert board["teams"][0]["score"] == 40


def test_admin_routes_require_admin(player) -> None:  # type: ignore[no-untyped-def]
    assert player.get("/api/admin/teams").status_code == 403
    assert player.get("/api/admin/submissions").status_code == 403
    assert player.post("/api/admin/announcements", {"title": "x", "body": "y"}).status_code == 403


def test_admin_submission_log(player, admin) -> None:  # type: ignore[no-untyped-def]
    player.submit("cesar", "DEMO{essai}")
    player.submit("cesar", "DEMO{jules_serait_fier}")
    log = admin.get("/api/admin/submissions").json()
    assert [(s["provided"], s["correct"], s["user"], s["team"]) for s in log] == [
        ("DEMO{jules_serait_fier}", True, "alice", "Les Testeurs"),
        ("DEMO{essai}", False, "alice", "Les Testeurs"),
    ]
    assert len(admin.get("/api/admin/submissions?correct=false").json()) == 1
    assert len(admin.get(f"/api/admin/submissions?before_id={log[0]['id']}").json()) == 1


def test_admin_sees_challenges_without_team(admin, sync, clock) -> None:  # type: ignore[no-untyped-def]
    sync()
    clock.set(datetime(2025, 1, 1, tzinfo=UTC))
    assert len(admin.get("/api/challenges").json()["challenges"]) == 6


def test_announcements(admin, new_client) -> None:  # type: ignore[no-untyped-def]
    response = admin.post(
        "/api/admin/announcements", {"title": "Indice", "body": "**Gras** <script>x</script>"}
    )
    assert response.status_code == 201
    listing = new_client().get("/api/announcements").json()
    assert listing[0]["title"] == "Indice"
    assert "<strong>Gras</strong>" in listing[0]["body_html"]
    assert "<script" not in listing[0]["body_html"]
    assert admin.delete(f"/api/admin/announcements/{listing[0]['id']}").status_code == 204
    assert new_client().get("/api/announcements").json() == []
