from pathlib import Path

import pytest
import yaml

from jacquard.packs.loader import PackError, load_pack

from .conftest import DEMO_PACK


def errors_of(path: Path) -> list[str]:
    with pytest.raises(PackError) as info:
        load_pack(path)
    return [str(e) for e in info.value.errors]


def write_challenge(
    pack: Path, data: dict[str, object], description: str | None = "Texte", folder: str = "nouveau"
) -> Path:
    directory = pack / "challenges" / "misc" / folder
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "challenge.yml").write_text(yaml.safe_dump(data), encoding="utf-8")
    if description is not None:
        (directory / "description.md").write_text(description, encoding="utf-8")
    return directory


BASE = {
    "id": "nouveau",
    "name": "Nouveau",
    "category": "misc",
    "flags": [{"type": "static", "value": "DEMO{x}"}],
}


def test_demo_pack_is_valid() -> None:
    pack = load_pack(DEMO_PACK)
    assert pack.event.id == "demo"
    assert {c.config.id for c in pack.challenges} == {
        "bienvenue",
        "cesar",
        "couches",
        "ville",
        "avance",
        "coffre",
    }
    assert [s.config.id for s in pack.story] == ["prologue", "premier-pas", "final"]
    assert pack.warnings == []
    assert pack.event.schedule.start.tzinfo is not None


def test_digest_is_stable() -> None:
    assert load_pack(DEMO_PACK).digest == load_pack(DEMO_PACK).digest


def test_unknown_category(make_pack) -> None:  # type: ignore[no-untyped-def]
    pack = make_pack()
    write_challenge(pack, {**BASE, "category": "inexistante"})
    assert any("catégorie inconnue" in e for e in errors_of(pack))


def test_unknown_field_is_rejected(make_pack) -> None:  # type: ignore[no-untyped-def]
    pack = make_pack()
    write_challenge(pack, {**BASE, "bonus_secret": 42})
    assert any("champ inconnu" in e for e in errors_of(pack))


def test_duplicate_ids(make_pack) -> None:  # type: ignore[no-untyped-def]
    pack = make_pack()
    write_challenge(pack, {**BASE, "id": "bienvenue"}, folder="copie")
    assert any("id déjà utilisé" in e for e in errors_of(pack))


@pytest.mark.parametrize("entry", ["../../../../dehors.txt", "/etc/passwd"])
def test_files_must_stay_inside_pack(make_pack, entry: str) -> None:  # type: ignore[no-untyped-def]
    pack = make_pack()
    (pack.parent / "dehors.txt").write_text("hors du pack")
    write_challenge(pack, {**BASE, "files": [entry]})
    assert any("hors du pack" in e for e in errors_of(pack))


def test_symlink_escaping_pack_is_rejected(make_pack, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    pack = make_pack()
    secret = tmp_path / "secret.txt"
    secret.write_text("secret")
    directory = write_challenge(pack, {**BASE, "files": ["lien.txt"]})
    (directory / "lien.txt").symlink_to(secret)
    assert any("hors du pack" in e for e in errors_of(pack))


def test_solution_files_cannot_be_distributed(make_pack) -> None:  # type: ignore[no-untyped-def]
    pack = make_pack()
    directory = write_challenge(pack, {**BASE, "files": ["solution/writeup.md"]})
    (directory / "solution").mkdir()
    (directory / "solution" / "writeup.md").write_text("réponse")
    assert any("solution" in e for e in errors_of(pack))


def test_missing_description_and_file(make_pack) -> None:  # type: ignore[no-untyped-def]
    pack = make_pack()
    write_challenge(pack, {**BASE, "files": ["absent.bin"]}, description=None)
    errors = errors_of(pack)
    assert any("description introuvable" in e for e in errors)
    assert any("fichier introuvable" in e for e in errors)


def test_invalid_regex(make_pack) -> None:  # type: ignore[no-untyped-def]
    pack = make_pack()
    write_challenge(pack, {**BASE, "flags": [{"type": "regex", "pattern": "DEMO{(}"}]})
    assert any("expression régulière invalide" in e for e in errors_of(pack))


def test_schedule_must_be_consistent(make_pack) -> None:  # type: ignore[no-untyped-def]
    pack = make_pack(schedule={"start": "2027-01-02T00:00:00", "end": "2027-01-01T00:00:00"})
    assert any("schedule.end" in e for e in errors_of(pack))


def test_flag_format_mismatch_is_a_warning(make_pack) -> None:  # type: ignore[no-untyped-def]
    pack = make_pack()
    write_challenge(pack, {**BASE, "flags": [{"type": "static", "value": "AUTRE{x}"}]})
    loaded = load_pack(pack)
    assert any("format" in str(w) for w in loaded.warnings)


def test_invalid_yaml(make_pack) -> None:  # type: ignore[no-untyped-def]
    pack = make_pack()
    (pack / "event.yml").write_text("id: [non fermé", encoding="utf-8")
    assert any("YAML invalide" in e for e in errors_of(pack))


def test_rule_references_must_exist(make_pack) -> None:  # type: ignore[no-untyped-def]
    pack = make_pack()
    write_challenge(
        pack,
        {
            **BASE,
            "unlock": {"all": [{"solved": "fantome"}, {"item": "inconnu"}, {"hint_used": "nope"}]},
        },
    )
    errors = errors_of(pack)
    assert any("défi inconnu : fantome" in e for e in errors)
    assert any("objet inconnu : inconnu" in e for e in errors)
    assert any("indice inconnu : nope" in e for e in errors)


def test_circular_dependency_is_detected(make_pack) -> None:  # type: ignore[no-untyped-def]
    pack = make_pack()
    write_challenge(pack, {**BASE, "id": "poule", "unlock": {"solved": "oeuf"}}, folder="poule")
    write_challenge(pack, {**BASE, "id": "oeuf", "unlock": {"solved": "poule"}}, folder="oeuf")
    errors = [e for e in errors_of(pack) if "impossible à débloquer" in e]
    assert len(errors) == 2


def test_granted_item_must_be_declared(make_pack) -> None:  # type: ignore[no-untyped-def]
    pack = make_pack()
    write_challenge(pack, {**BASE, "on_solve": [{"grant_item": "pas-declare"}]})
    assert any("objet non déclaré" in e for e in errors_of(pack))


def test_hint_ids_are_global(make_pack) -> None:  # type: ignore[no-untyped-def]
    pack = make_pack()
    write_challenge(pack, {**BASE, "hints": [{"id": "cesar-1", "text": "doublon"}]})
    assert any("id d'indice déjà utilisé" in e for e in errors_of(pack))


def test_unused_item_and_hidden_locked_message_warn(make_pack) -> None:  # type: ignore[no-untyped-def]
    demo_items = yaml.safe_load((DEMO_PACK / "event.yml").read_text(encoding="utf-8"))["items"]
    pack = make_pack(items=[*demo_items, {"id": "orphelin", "name": "Orphelin"}])
    write_challenge(pack, {**BASE, "unlock": {"solved": "bienvenue"}, "locked_message": "x"})
    warnings = [str(w) for w in load_pack(pack).warnings]
    assert any("orphelin" in w for w in warnings)
    assert any("locked_message" in w for w in warnings)


def test_story_front_matter(make_pack) -> None:  # type: ignore[no-untyped-def]
    pack = make_pack()
    (pack / "story" / "03-sans-entete.md").write_text("Pas d'en-tête", encoding="utf-8")
    (pack / "story" / "04-non-ferme.md").write_text("---\nid: x\ntitle: X\n", encoding="utf-8")
    (pack / "story" / "05-public.md").write_text(
        "---\nid: p\ntitle: P\npublic: true\nunlock: { solved: cesar }\n---\nTexte",
        encoding="utf-8",
    )
    errors = errors_of(pack)
    assert any("en-tête YAML manquant" in e for e in errors)
    assert any("non fermé" in e for e in errors)
    assert any("chapitre public" in e for e in errors)


def test_impossible_story_is_a_warning(make_pack) -> None:  # type: ignore[no-untyped-def]
    pack = make_pack()
    (pack / "story" / "09-jamais.md").write_text(
        "---\nid: jamais\ntitle: Jamais\nunlock: { score: { gte: 999999 } }\n---\nTexte",
        encoding="utf-8",
    )
    assert any("jamais" in str(w) for w in load_pack(pack).warnings)


def test_challenge_host_placeholder(make_pack, db, sync) -> None:  # type: ignore[no-untyped-def]
    from jacquard.models import Challenge

    pack = make_pack()
    write_challenge(pack, {**BASE, "connection": "nc {challenge_host} 4000"})
    assert any("challenge_host" in e for e in errors_of(pack))

    pack = make_pack(challenge_host="defis.example.org")
    write_challenge(pack, {**BASE, "connection": "nc {challenge_host} 4000"})
    sync(pack)
    assert db.get(Challenge, "nouveau").connection == "nc defis.example.org 4000"


def test_rehearsal_shifts_schedule() -> None:
    from datetime import UTC, datetime, timedelta

    from jacquard.packs.rehearsal import shift_schedule

    pack = load_pack(DEMO_PACK)
    original = pack.event.schedule
    start = datetime(2026, 11, 3, 13, 0, tzinfo=UTC)
    shifted = shift_schedule(pack, start)
    assert shifted.event.schedule.start == start
    assert shifted.event.schedule.end - start == original.end - original.start
    assert shifted.digest != pack.digest
    assert pack.event.schedule == original  # l'original n'est pas modifié
    assert len(shifted.digest) == 64
    assert shifted.event.schedule.end > start + timedelta(hours=1)


def test_cli_start_now(make_pack, tmp_path) -> None:  # type: ignore[no-untyped-def]
    from typer.testing import CliRunner

    from jacquard.cli import app
    from jacquard.db import get_sessionmaker
    from jacquard.services import load_event

    pack = make_pack(
        schedule={
            "start": "2030-01-01T10:00:00",
            "end": "2030-01-01T16:00:00",
            "freeze": "2030-01-01T15:30:00",
        }
    )
    result = CliRunner().invoke(app, ["pack", "sync", str(pack), "--start-now"])
    assert result.exit_code == 0, result.output
    assert "Répétition" in result.output
    with get_sessionmaker()() as db:
        event = load_event(db)
    assert event is not None
    from jacquard.clock import utcnow

    assert abs((event.schedule.start - utcnow()).total_seconds()) < 60
    assert event.schedule.end - event.schedule.start == timedelta_hours(6)
    assert event.schedule.end - event.schedule.freeze == timedelta_hours(0.5)


def timedelta_hours(hours: float):  # type: ignore[no-untyped-def]
    from datetime import timedelta

    return timedelta(hours=hours)
