def test_create_and_join_team(player, new_client) -> None:  # type: ignore[no-untyped-def]
    team = player.get("/api/teams/me").json()
    assert team["name"] == "Les Testeurs"
    assert [m["username"] for m in team["members"]] == ["alice"]

    bob = new_client()
    bob.register("bob")
    joined = bob.post("/api/teams/join", {"invite_code": team["invite_code"].lower()})
    assert joined.status_code == 200
    assert [m["username"] for m in joined.json()["members"]] == ["alice", "bob"]
    assert bob.get("/api/auth/me").json()["team"]["name"] == "Les Testeurs"


def test_team_name_is_unique_and_normalized(player, new_client) -> None:  # type: ignore[no-untyped-def]
    bob = new_client()
    bob.register("bob")
    assert bob.post("/api/teams", {"name": "  les   TESTEURS "}).status_code == 409
    assert bob.post("/api/teams", {"name": "x"}).status_code == 422
    assert bob.post("/api/teams", {"name": "Équipe\x00nulle"}).status_code == 422


def test_cannot_have_two_teams(player) -> None:  # type: ignore[no-untyped-def]
    assert player.post("/api/teams", {"name": "Deuxième"}).status_code == 409


def test_invalid_invite_code(new_client, sync) -> None:  # type: ignore[no-untyped-def]
    sync()
    api = new_client()
    api.register("bob")
    assert api.post("/api/teams/join", {"invite_code": "NIMPORTEQUOI"}).status_code == 404


def test_team_size_is_enforced(player, new_client) -> None:  # type: ignore[no-untyped-def]
    code = player.get("/api/teams/me").json()["invite_code"]
    for name in ("bob", "carol", "dave"):
        member = new_client()
        member.register(name)
        assert member.post("/api/teams/join", {"invite_code": code}).status_code == 200
    late = new_client()
    late.register("eve")
    response = late.post("/api/teams/join", {"invite_code": code})
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "team_full"


def test_leave_team_without_solves_deletes_empty_team(player, new_client) -> None:  # type: ignore[no-untyped-def]
    assert player.post("/api/teams/leave").status_code == 204
    assert player.get("/api/teams/me").json() is None
    bob = new_client()
    bob.register("bob")
    # Le nom est libéré puisque l'équipe vide a été supprimée.
    assert bob.post("/api/teams", {"name": "Les Testeurs"}).status_code == 201


def test_cannot_leave_team_with_solves(player) -> None:  # type: ignore[no-untyped-def]
    assert player.submit("bienvenue", "DEMO{bienvenue_a_bord}").json()["status"] == "correct"
    response = player.post("/api/teams/leave")
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "team_has_solves"


def test_team_view_contains_real_score(player) -> None:  # type: ignore[no-untyped-def]
    player.submit("bienvenue", "DEMO{bienvenue_a_bord}")
    team = player.get("/api/teams/me").json()
    # 10 points statiques + 30 de premier sang.
    assert team["score"] == 40
    assert team["rank"] == 1
    assert team["solves"][0]["challenge_id"] == "bienvenue"
    assert team["solves"][0]["solved_by"] == "alice"
