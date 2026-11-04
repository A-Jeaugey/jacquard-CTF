"""Mécaniques de progression : déblocages, objets, indices, histoire."""

from datetime import timedelta
from pathlib import Path
from typing import Any

import yaml


def add_challenge(pack: Path, data: dict[str, Any], description: str = "Texte") -> None:
    directory = pack / "challenges" / data["category"] / data["id"]
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "challenge.yml").write_text(yaml.safe_dump(data), encoding="utf-8")
    (directory / "description.md").write_text(description, encoding="utf-8")


def edit_challenge(pack: Path, path: str, **changes: Any) -> None:
    manifest = pack / "challenges" / path / "challenge.yml"
    data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    data.update(changes)
    manifest.write_text(yaml.safe_dump(data), encoding="utf-8")


def listing(api) -> dict[str, dict[str, Any]]:  # type: ignore[no-untyped-def]
    return {c["id"]: c for c in api.get("/api/challenges").json()["challenges"]}


# --------------------------------------------------------------------------- déblocages


def test_locked_challenges_do_not_leak(player) -> None:  # type: ignore[no-untyped-def]
    challenges = listing(player)
    assert "coffre" not in challenges  # caché
    avance = challenges["avance"]  # annoncé
    assert avance["locked"] is True
    assert avance["locked_message"] == "Résous deux défis de cryptographie pour débloquer ce défi."

    response = player.get("/api/challenges/avance")
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "locked"
    assert "niveau_superieur" not in response.text
    assert player.submit("avance", "DEMO{niveau_superieur}").status_code == 403

    # Le défi caché répond exactement comme un défi inexistant.
    hidden = player.get("/api/challenges/coffre")
    missing = player.get("/api/challenges/inexistant")
    assert hidden.status_code == missing.status_code == 404
    assert hidden.json() == missing.json()
    assert player.submit("coffre", "DEMO{coffre_ouvert}").status_code == 404


def test_solved_count_unlocks_teaser(player) -> None:  # type: ignore[no-untyped-def]
    player.submit("cesar", "DEMO{jules_serait_fier}")
    result = player.submit("couches", "DEMO{trois_couches_suffisent}").json()
    assert result["unlocked"]["challenges"] == [{"id": "avance", "name": "Niveau supérieur"}]
    assert listing(player)["avance"]["locked"] is False
    assert "niveau_superieur" in player.get("/api/challenges/avance").json()["description_html"]
    assert player.submit("avance", "DEMO{niveau_superieur}").json()["status"] == "correct"


def test_items_unlock_the_hidden_final(player) -> None:  # type: ignore[no-untyped-def]
    first = player.submit("couches", "DEMO{trois_couches_suffisent}").json()
    assert [i["id"] for i in first["items"]] == ["cle-crypto"]
    assert "coffre" not in listing(player)

    second = player.submit("ville", "DEMO{lyon}").json()
    assert [i["name"] for i in second["items"]] == ["Clé d'OSINT"]
    assert {"id": "coffre", "name": "Le coffre"} in second["unlocked"]["challenges"]

    team = player.get("/api/teams/me").json()
    assert [i["id"] for i in team["items"]] == ["cle-crypto", "cle-osint"]

    final = player.submit("coffre", "DEMO{coffre_ouvert}").json()
    assert final["status"] == "correct"
    assert "Félicitations" in final["notifications"][0]
    assert final["unlocked"]["story"] == [{"id": "final", "title": "Le coffre est ouvert"}]


def test_other_teams_are_not_affected(player, new_client) -> None:  # type: ignore[no-untyped-def]
    player.submit("couches", "DEMO{trois_couches_suffisent}")
    player.submit("ville", "DEMO{lyon}")
    bob = new_client()
    bob.register("bob")
    bob.create_team("Autre équipe")
    assert "coffre" not in listing(bob)
    assert bob.get("/api/teams/me").json()["items"] == []


def test_unlocks_are_sticky(new_client, sync, make_pack) -> None:  # type: ignore[no-untyped-def]
    pack = make_pack()
    add_challenge(
        pack,
        {
            "id": "riche",
            "name": "Réservé aux riches",
            "category": "misc",
            "unlock": {"score": {"gte": 500}},
            "flags": [{"type": "static", "value": "DEMO{riche}"}],
        },
    )
    sync(pack)
    api = new_client()
    api.register("alice")
    api.create_team("Alpha")
    api.submit("cesar", "DEMO{jules_serait_fier}")  # 500 + 30 de premier sang
    assert "riche" in listing(api)
    api.post("/api/challenges/cesar/hints/cesar-2/unlock")  # -50 : score 480
    assert api.get("/api/teams/me").json()["score"] == 480
    assert "riche" in listing(api)


def test_listing_names_visible_prerequisites_only(new_client, sync, make_pack) -> None:  # type: ignore[no-untyped-def]
    pack = make_pack()
    # Après « César », à heure fixe ; un prérequis caché (« coffre ») n'est jamais nommé.
    add_challenge(
        pack,
        {
            "id": "suite",
            "name": "La suite",
            "category": "misc",
            "unlock": {"all": [{"solved": "cesar"}, {"time": {"elapsed_minutes": 0}}]},
            "when_locked": "teaser",
            "flags": [{"type": "static", "value": "DEMO{suite}"}],
        },
    )
    add_challenge(
        pack,
        {
            "id": "apres-coffre",
            "name": "Après le coffre",
            "category": "misc",
            "unlock": {"any": [{"solved": "coffre"}, {"not": {"solved": "cesar"}}]},
            "flags": [{"type": "static", "value": "DEMO{apres}"}],
        },
    )
    sync(pack)
    api = new_client()
    api.register("alice")
    api.create_team("Alpha")
    challenges = listing(api)
    assert challenges["suite"]["after"] == ["cesar"]
    assert challenges["suite"]["opens_at"] is not None
    assert challenges["cesar"]["after"] == []
    assert challenges["cesar"]["opens_at"] is None
    # « coffre » est caché pour l'équipe, la branche « not » n'ouvre rien : rien n'est nommé.
    assert "coffre" not in challenges
    assert challenges["apres-coffre"]["after"] == []
    assert '"coffre"' not in api.get("/api/challenges").text


def test_locked_challenge_files_are_hidden(new_client, sync, make_pack) -> None:  # type: ignore[no-untyped-def]
    pack = make_pack()
    edit_challenge(pack, "crypto/cesar", unlock={"solved": "bienvenue"}, when_locked="teaser")
    sync(pack)
    admin_view = None
    api = new_client()
    api.register("alice")
    api.create_team("Alpha")
    assert api.get("/api/challenges/cesar").status_code == 403

    from jacquard.db import get_sessionmaker
    from jacquard.models import ChallengeFile

    with get_sessionmaker()() as db:
        admin_view = db.query(ChallengeFile).filter_by(challenge_id="cesar").one().id
    assert api.get(f"/api/files/{admin_view}").status_code == 404
    api.submit("bienvenue", "DEMO{bienvenue_a_bord}")
    assert api.get(f"/api/files/{admin_view}").status_code == 200


def test_admin_sees_everything_with_rules(admin, sync) -> None:  # type: ignore[no-untyped-def]
    sync()
    challenges = listing(admin)
    assert challenges["coffre"]["locked"] is False
    assert challenges["coffre"]["unlock"] == {
        "all": [{"item": "cle-crypto"}, {"item": "cle-osint"}]
    }
    assert admin.get("/api/challenges/coffre").status_code == 200


# --------------------------------------------------------------------------- indices


def hints_of(api, challenge_id: str) -> dict[str, dict[str, Any]]:  # type: ignore[no-untyped-def]
    return {h["id"]: h for h in api.get(f"/api/challenges/{challenge_id}").json()["hints"]}


def test_hint_text_is_hidden_until_bought(player) -> None:  # type: ignore[no-untyped-def]
    hints = hints_of(player, "cesar")
    assert hints["cesar-1"] == {
        "id": "cesar-1",
        "cost": 0,
        "available": True,
        "unlocked": False,
        "text_html": None,
    }
    assert "ROT13" not in player.get("/api/challenges/cesar").text

    response = player.post("/api/challenges/cesar/hints/cesar-2/unlock")
    assert response.status_code == 200
    assert "ROT13" in response.json()["text_html"]
    assert hints_of(player, "cesar")["cesar-2"]["unlocked"] is True

    team = player.get("/api/teams/me").json()
    assert team["penalty"] == 50
    assert team["score"] == -50

    # Racheter ne coûte rien de plus.
    player.post("/api/challenges/cesar/hints/cesar-2/unlock")
    assert player.get("/api/teams/me").json()["score"] == -50


def test_hint_must_belong_to_challenge(player) -> None:  # type: ignore[no-untyped-def]
    assert player.post("/api/challenges/couches/hints/cesar-1/unlock").status_code == 404
    assert player.post("/api/challenges/cesar/hints/inconnu/unlock").status_code == 404
    # Indice d'un défi caché : même réponse qu'un défi inexistant.
    assert player.post("/api/challenges/coffre/hints/cesar-1/unlock").status_code == 404


def test_hint_can_require_points(new_client, sync, make_pack) -> None:  # type: ignore[no-untyped-def]
    sync(make_pack(hints={"require_points": True}))
    api = new_client()
    api.register("alice")
    api.create_team("Alpha")
    response = api.post("/api/challenges/cesar/hints/cesar-2/unlock")
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "not_enough_points"
    assert api.post("/api/challenges/cesar/hints/cesar-1/unlock").status_code == 200  # gratuit
    api.submit("ville", "DEMO{lyon}")
    assert api.post("/api/challenges/cesar/hints/cesar-2/unlock").status_code == 200


def test_timed_hint(new_client, sync, make_pack, clock) -> None:  # type: ignore[no-untyped-def]
    # Début de l'événement 10 minutes avant l'horloge de test (12:00 UTC = 14:00 à Paris).
    sync(make_pack(schedule={"start": "2027-06-01T13:50:00", "end": "2027-06-01T20:00:00"}))
    api = new_client()
    api.register("alice")
    api.create_team("Alpha")
    assert hints_of(api, "ville")["ville-1"]["available"] is False
    response = api.post("/api/challenges/ville/hints/ville-1/unlock")
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "hint_unavailable"
    clock.set(clock.now + timedelta(minutes=20))
    assert hints_of(api, "ville")["ville-1"]["available"] is True
    assert api.post("/api/challenges/ville/hints/ville-1/unlock").status_code == 200


def test_hint_penalties_respect_freeze(new_client, sync, make_pack, clock) -> None:  # type: ignore[no-untyped-def]
    sync(
        make_pack(
            schedule={
                "start": "2027-06-01T10:00:00",
                "end": "2027-06-01T18:00:00",
                "freeze": "2027-06-01T15:00:00",
            }
        )
    )
    api = new_client()
    api.register("alice")
    api.create_team("Alpha")
    api.submit("ville", "DEMO{lyon}")
    clock.set(clock.now + timedelta(hours=2))  # après le gel
    api.post("/api/challenges/cesar/hints/cesar-2/unlock")
    public = new_client().get("/api/scoreboard").json()
    assert public["teams"][0]["score"] == 80
    assert api.get("/api/teams/me").json()["score"] == 30


# --------------------------------------------------------------------------- histoire


def test_story_visibility(player, new_client, admin) -> None:  # type: ignore[no-untyped-def]
    anonymous = new_client().get("/api/story").json()
    assert [e["id"] for e in anonymous["entries"]] == ["prologue"]
    assert anonymous["locked"] == 2

    assert [e["id"] for e in player.get("/api/story").json()["entries"]] == ["prologue"]
    result = player.submit("bienvenue", "DEMO{bienvenue_a_bord}").json()
    assert result["unlocked"]["story"] == [{"id": "premier-pas", "title": "Premiers pas"}]
    assert "journal" in result["notifications"][0]
    story = player.get("/api/story").json()
    assert [e["id"] for e in story["entries"]] == ["prologue", "premier-pas"]
    assert "<strong>cryptographie</strong>" in story["entries"][1]["body_html"]
    assert story["locked"] == 1

    assert len(admin.get("/api/story").json()["entries"]) == 3


def test_story_hidden_before_start(player, clock) -> None:  # type: ignore[no-untyped-def]
    player.submit("bienvenue", "DEMO{bienvenue_a_bord}")
    from datetime import UTC, datetime

    clock.set(datetime(2025, 1, 1, tzinfo=UTC))
    player.post("/api/auth/login", {"username": "alice", "password": "motdepasse-solide"})
    assert [e["id"] for e in player.get("/api/story").json()["entries"]] == ["prologue"]


def test_resync_keeps_progress(player, sync, make_pack) -> None:  # type: ignore[no-untyped-def]
    player.submit("cesar", "DEMO{jules_serait_fier}")
    player.submit("couches", "DEMO{trois_couches_suffisent}")
    player.post("/api/challenges/cesar/hints/cesar-1/unlock")
    pack = make_pack()
    edit_challenge(pack, "crypto/cesar", name="Ave César (corrigé)")
    sync(pack)
    challenges = listing(player)
    assert challenges["cesar"]["name"] == "Ave César (corrigé)"
    assert challenges["avance"]["locked"] is False
    assert hints_of(player, "cesar")["cesar-1"]["unlocked"] is True
