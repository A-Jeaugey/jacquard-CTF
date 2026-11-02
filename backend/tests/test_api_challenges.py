import json
from datetime import UTC, datetime, timedelta

import pytest

DEMO_START = datetime(2025, 12, 31, 23, 0, tzinfo=UTC)  # 2026-01-01T00:00 Europe/Paris
DEMO_END = datetime(2029, 12, 31, 23, 0, tzinfo=UTC)


def test_challenge_list(player) -> None:  # type: ignore[no-untyped-def]
    data = player.get("/api/challenges").json()
    assert data["phase"] == "running"
    ids = [c["id"] for c in data["challenges"]]
    assert ids[0] == "bienvenue"  # position 0
    assert set(ids) == {"bienvenue", "cesar", "couches", "ville"}
    cesar = next(c for c in data["challenges"] if c["id"] == "cesar")
    assert cesar == {
        "id": "cesar",
        "name": "Ave César",
        "category": "crypto",
        "difficulty": "facile",
        "tags": [],
        "value": 500,
        "solves": 0,
        "solved": False,
    }


def test_flags_never_leak(player) -> None:  # type: ignore[no-untyped-def]
    payloads = [
        player.get("/api/challenges").text,
        *(
            player.get(f"/api/challenges/{cid}").text
            for cid in ("bienvenue", "cesar", "couches", "ville")
        ),
    ]
    for payload in payloads:
        assert "jules_serait_fier" not in payload
        assert "trois_couches" not in payload
        assert "lugdunum" not in payload.lower()
        assert "flags" not in json.loads(payload)


def test_challenge_detail_renders_safe_markdown(player) -> None:  # type: ignore[no-untyped-def]
    detail = player.get("/api/challenges/bienvenue").json()
    assert "<code>DEMO{bienvenue_a_bord}</code>" in detail["description_html"]
    assert detail["files"] == []


def test_markdown_is_sanitized() -> None:
    from jacquard.markdown import render_markdown

    html = render_markdown(
        "<script>alert(1)</script>\n\n[x](javascript:alert(1))\n\n<img src=x onerror=alert(1)>"
    )
    # Le HTML brut est échappé et les liens dangereux ne deviennent pas des liens.
    assert "<script" not in html
    assert "<img" not in html
    assert "href=" not in html


def test_correct_incorrect_and_already_solved(player) -> None:  # type: ignore[no-untyped-def]
    assert player.submit("cesar", "DEMO{faux}").json() == {"status": "incorrect"}
    assert player.submit("cesar", "  demo{JULES_SERAIT_FIER} ").json() == {"status": "correct"}
    assert player.submit("cesar", "DEMO{jules_serait_fier}").json() == {"status": "already_solved"}
    listing = player.get("/api/challenges").json()["challenges"]
    assert next(c for c in listing if c["id"] == "cesar")["solved"] is True


def test_case_sensitive_flag(player) -> None:  # type: ignore[no-untyped-def]
    assert player.submit("couches", "demo{trois_couches_suffisent}").json()["status"] == "incorrect"
    assert player.submit("couches", "DEMO{trois_couches_suffisent}").json()["status"] == "correct"


@pytest.mark.parametrize(
    ("flag", "expected"),
    [
        ("DEMO{lyon}", "correct"),
        ("demo{LUGDUNUM}", "correct"),
        ("DEMO{lyon}x", "incorrect"),
        ("DEMO{paris}", "incorrect"),
    ],
)
def test_regex_flag_is_anchored(player, flag: str, expected: str) -> None:  # type: ignore[no-untyped-def]
    assert player.submit("ville", flag).json()["status"] == expected


def test_submission_rate_limit(player) -> None:  # type: ignore[no-untyped-def]
    for _ in range(10):
        assert player.submit("cesar", "DEMO{faux}").status_code == 200
    response = player.submit("cesar", "DEMO{jules_serait_fier}")
    assert response.status_code == 429
    assert response.json()["detail"]["retry_after"] >= 1


def test_rate_limit_window_slides(player, clock) -> None:  # type: ignore[no-untyped-def]
    for _ in range(10):
        player.submit("cesar", "DEMO{faux}")
    clock.set(clock.now + timedelta(seconds=61))
    assert player.submit("cesar", "DEMO{jules_serait_fier}").json()["status"] == "correct"


def test_unknown_challenge(player) -> None:  # type: ignore[no-untyped-def]
    assert player.get("/api/challenges/inexistant").status_code == 404
    assert player.submit("inexistant", "x").status_code == 404


def test_requires_team(new_client, sync) -> None:  # type: ignore[no-untyped-def]
    sync()
    api = new_client()
    api.register("solitaire")
    assert api.get("/api/challenges").json()["challenges"] == []
    assert api.get("/api/challenges/bienvenue").status_code == 403
    assert api.submit("bienvenue", "DEMO{bienvenue_a_bord}").status_code == 403


def test_requires_login(new_client, sync) -> None:  # type: ignore[no-untyped-def]
    sync()
    api = new_client()
    assert api.get("/api/challenges").status_code == 401
    assert api.submit("bienvenue", "x").status_code == 401


def test_nothing_visible_before_start(player, clock) -> None:  # type: ignore[no-untyped-def]
    clock.set(DEMO_START - timedelta(seconds=1))
    data = player.get("/api/challenges").json()
    assert data == {"phase": "not_started", "challenges": []}
    assert player.get("/api/challenges/bienvenue").status_code == 403
    response = player.submit("bienvenue", "DEMO{bienvenue_a_bord}")
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "event_not_started"


def test_submissions_closed_after_end(player, clock) -> None:  # type: ignore[no-untyped-def]
    clock.set(DEMO_END)
    player.post("/api/auth/login", {"username": "alice", "password": "motdepasse-solide"})
    assert player.get("/api/challenges").json()["phase"] == "ended"
    assert len(player.get("/api/challenges").json()["challenges"]) == 4
    response = player.submit("bienvenue", "DEMO{bienvenue_a_bord}")
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "event_ended"


def test_file_download(player) -> None:  # type: ignore[no-untyped-def]
    files = player.get("/api/challenges/cesar").json()["files"]
    assert [f["name"] for f in files] == ["message.txt"]
    response = player.get(f"/api/files/{files[0]['id']}")
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    assert response.headers["content-type"] == "application/octet-stream"
    assert "QRZB{" in response.text  # « DEMO{ » en ROT13


def test_file_hidden_before_start_and_without_team(player, new_client, clock) -> None:  # type: ignore[no-untyped-def]
    file_id = player.get("/api/challenges/cesar").json()["files"][0]["id"]
    outsider = new_client()
    outsider.register("bob")
    assert outsider.get(f"/api/files/{file_id}").status_code == 404
    assert new_client().get(f"/api/files/{file_id}").status_code == 401
    clock.set(DEMO_START - timedelta(seconds=1))
    assert player.get(f"/api/files/{file_id}").status_code == 404
    assert player.get("/api/files/inexistant").status_code == 404


def test_removed_challenge_is_deactivated_but_solves_kept(player, sync, make_pack, db) -> None:  # type: ignore[no-untyped-def]
    import shutil

    from jacquard.models import Solve

    player.submit("cesar", "DEMO{jules_serait_fier}")
    pack = make_pack()
    shutil.rmtree(pack / "challenges" / "crypto" / "cesar")
    sync(pack)
    assert "cesar" not in [c["id"] for c in player.get("/api/challenges").json()["challenges"]]
    assert player.get("/api/challenges/cesar").status_code == 404
    assert db.query(Solve).count() == 1
    assert player.get("/api/teams/me").json()["score"] == 0

    sync()  # le défi revient : la résolution compte de nouveau
    assert player.get("/api/teams/me").json()["score"] == 530
