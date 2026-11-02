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
    assert {c.config.id for c in pack.challenges} == {"bienvenue", "cesar", "couches", "ville"}
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
    write_challenge(pack, {**BASE, "unlock": {"solved": "bienvenue"}})
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
