"""Thème, layouts image-map, grand écran et fil d'actualité."""

import json
from datetime import timedelta
from pathlib import Path

import psycopg
import pytest
import yaml

from jacquard.packs.loader import PackError, load_pack

from .conftest import DEMO_PACK
from .test_realtime import CHANNEL, _psycopg_dsn


def edit_theme(pack: Path, **changes: object) -> None:
    path = pack / "theme" / "theme.yml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data.update(changes)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


def errors_of(pack: Path) -> list[str]:
    with pytest.raises(PackError) as info:
        load_pack(pack)
    return [str(e) for e in info.value.errors]


# --------------------------------------------------------------------------- validation


def test_demo_theme_is_loaded() -> None:
    pack = load_pack(DEMO_PACK)
    assert pack.theme is not None
    assert set(pack.theme.config.layouts) == {"carte"}
    assert {a.path for a in pack.theme.assets} == {"theme.css", "layouts/carte.svg"}
    assert pack.warnings == []


@pytest.mark.parametrize(
    "payload",
    [
        "<script>alert(1)</script>",
        '<rect onload="alert(1)"/>',
        '<a href="javascript:alert(1)"><rect/></a>',
        '<image href="https://evil.example/x.png"/>',
        "<foreignObject><div>x</div></foreignObject>",
    ],
)
def test_dangerous_svg_is_rejected(make_pack, payload: str) -> None:  # type: ignore[no-untyped-def]
    pack = make_pack()
    svg = pack / "theme" / "layouts" / "carte.svg"
    svg.write_text(svg.read_text().replace("</svg>", payload + "</svg>"))
    assert any("contenu interdit" in e for e in errors_of(pack))


def test_external_css_is_rejected(make_pack) -> None:  # type: ignore[no-untyped-def]
    pack = make_pack()
    (pack / "theme" / "theme.css").write_text("@import url('https://evil.example/x.css');")
    assert any("contenu interdit" in e for e in errors_of(pack))


def test_token_values_cannot_escape_css(make_pack) -> None:  # type: ignore[no-untyped-def]
    pack = make_pack()
    edit_theme(pack, tokens={"color-bg": "red; } body { display: none"})
    assert errors_of(pack)


def test_zone_references_are_checked(make_pack) -> None:  # type: ignore[no-untyped-def]
    pack = make_pack()
    edit_theme(
        pack,
        layouts={
            "carte": {
                "type": "image-map",
                "background": "layouts/carte.svg",
                "zones": [
                    {"element": "#zone-misc", "target": {"category": "inconnue"}},
                    {"element": "#absent", "target": {"challenge": "cesar"}},
                    {"element": "#zone-osint", "target": {"challenge": "fantome"}},
                ],
            }
        },
    )
    errors = errors_of(pack)
    assert any("catégorie inconnue : inconnue" in e for e in errors)
    assert any("élément absent du SVG : #absent" in e for e in errors)
    assert any("défi inconnu : fantome" in e for e in errors)


def test_unknown_layouts_are_rejected(make_pack) -> None:  # type: ignore[no-untyped-def]
    pack = make_pack(board={"layout": "inexistant"}, screens=[{"id": "s", "layout": "grid"}])
    errors = errors_of(pack)
    assert any("layout inconnu : inexistant" in e for e in errors)
    assert any("layout de thème inconnu : grid" in e for e in errors)


def test_theme_files_must_stay_in_theme_dir(make_pack) -> None:  # type: ignore[no-untyped-def]
    pack = make_pack()
    edit_theme(pack, css="../event.yml")
    assert any("hors du dossier theme/" in e for e in errors_of(pack))


def test_reserved_layout_names(make_pack) -> None:  # type: ignore[no-untyped-def]
    pack = make_pack()
    data = yaml.safe_load((pack / "theme" / "theme.yml").read_text())
    data["layouts"]["grid"] = data["layouts"]["carte"]
    (pack / "theme" / "theme.yml").write_text(yaml.safe_dump(data))
    assert any("réservés" in e for e in errors_of(pack))


# --------------------------------------------------------------------------- API


def test_theme_api(new_client, sync) -> None:  # type: ignore[no-untyped-def]
    sync()
    api = new_client()
    theme = api.get("/api/theme").json()
    assert theme["tokens"]["color-accent"] == "#38bdf8"
    assert theme["strings"]["board.title"] == "Le plan du coffre"
    layout = theme["layouts"]["carte"]
    assert layout["type"] == "image-map"
    assert [z["target"] for z in layout["zones"]] == [
        {"category": "misc", "challenge": None},
        {"category": "crypto", "challenge": None},
        {"category": "osint", "challenge": None},
    ]
    svg = api.get(layout["background_url"])
    assert svg.status_code == 200
    assert svg.headers["content-type"].startswith("image/svg+xml")
    assert "zone-crypto" in svg.text
    # Même servi tel quel, le SVG ne peut rien exécuter : la CSP de l'API interdit tout.
    assert "default-src 'none'" in svg.headers["content-security-policy"]
    assert api.get(theme["css_url"]).headers["content-type"].startswith("text/css")
    assert api.get("/api/theme/assets/../event.yml").status_code == 404
    assert api.get("/api/theme/assets/inconnu.svg").status_code == 404


def test_theme_api_without_theme(new_client, sync, make_pack) -> None:  # type: ignore[no-untyped-def]
    import shutil

    pack = make_pack(board={"layout": "grid"}, screens=[])
    shutil.rmtree(pack / "theme")
    sync(pack)
    assert new_client().get("/api/theme").json() == {
        "tokens": {},
        "strings": {},
        "logo_url": None,
        "css_url": None,
        "layouts": {},
    }


def _team(new_client, name: str):  # type: ignore[no-untyped-def]
    api = new_client()
    api.register(name.lower())
    api.create_team(name)
    return api


def test_screen_progress(new_client, sync, admin) -> None:  # type: ignore[no-untyped-def]
    sync()
    alpha, bravo, orga_team = (
        _team(new_client, "Alpha"),
        _team(new_client, "Bravo"),
        _team(new_client, "Coulisses"),
    )
    admin.patch(f"/api/admin/teams/{orga_team.get('/api/teams/me').json()['id']}", {"hidden": True})
    alpha.submit("cesar", "DEMO{jules_serait_fier}")
    alpha.submit("couches", "DEMO{trois_couches_suffisent}")
    bravo.submit("cesar", "DEMO{jules_serait_fier}")
    orga_team.submit("ville", "DEMO{lyon}")  # équipe masquée : ne compte pas

    screen = new_client().get("/api/screens/projecteur").json()
    assert screen["title"] == "Démo : grand écran"
    assert screen["layout"] == "carte"
    assert screen["active_teams"] == 2
    progress = {c["id"]: c["progress"] for c in screen["categories"]}
    # crypto : 3 résolutions / (2 équipes × 3 défis actifs)
    assert progress == {"misc": 0.0, "crypto": pytest.approx(0.5), "osint": 0.0}
    assert "challenges" not in json.dumps(screen)
    assert new_client().get("/api/screens/inconnu").status_code == 404


def test_screen_respects_freeze(new_client, sync, make_pack, clock) -> None:  # type: ignore[no-untyped-def]
    sync(
        make_pack(
            schedule={
                "start": "2027-06-01T10:00:00",
                "end": "2027-06-01T18:00:00",
                "freeze": "2027-06-01T15:00:00",
            }
        )
    )
    alpha = _team(new_client, "Alpha")
    alpha.submit("cesar", "DEMO{jules_serait_fier}")
    clock.set(clock.now + timedelta(hours=2))
    alpha.post("/api/auth/login", {"username": "alpha", "password": "motdepasse-solide"})
    alpha.submit("couches", "DEMO{trois_couches_suffisent}")
    screen = new_client().get("/api/screens/projecteur").json()
    assert screen["frozen"] is True
    assert {c["id"]: c["progress"] for c in screen["categories"]}["crypto"] == pytest.approx(1 / 3)
    feed = new_client().get("/api/feed").json()
    assert [i["challenge"] for i in feed if i["kind"] == "first_blood"] == ["Ave César"]


def test_feed_hides_secret_challenges(new_client, sync, admin, clock) -> None:  # type: ignore[no-untyped-def]
    sync()
    alpha = _team(new_client, "Alpha")
    for challenge, flag in (("couches", "DEMO{trois_couches_suffisent}"), ("ville", "DEMO{lyon}")):
        clock.set(clock.now + timedelta(minutes=1))
        alpha.submit(challenge, flag)
    clock.set(clock.now + timedelta(minutes=1))
    with psycopg.connect(_psycopg_dsn(), autocommit=True) as conn:
        conn.execute(f"LISTEN {CHANNEL}")
        alpha.submit("coffre", "DEMO{coffre_ouvert}")
        events = [json.loads(n.payload) for n in conn.notifies(timeout=0.5, stop_after=10)]
    clock.set(clock.now + timedelta(minutes=1))
    admin.post("/api/admin/announcements", {"title": "Pause", "body": "Pizzas !"})

    solve = next(e for e in events if e["type"] == "solve")
    assert solve["data"]["challenge"] == "un défi secret"
    assert solve["data"]["challenge_id"] is None
    assert "coffre" not in json.dumps(solve).lower()

    feed = new_client().get("/api/feed").json()
    assert feed[0] == {"kind": "announcement", "at": feed[0]["at"], "title": "Pause"}
    names = [i["challenge"] for i in feed if i["kind"] == "first_blood"]
    assert names == ["un défi secret", "Quelle ville ?", "Mille-feuille"]
