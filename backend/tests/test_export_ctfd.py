from pathlib import Path

import yaml

from jacquard.packs.export_ctfd import export_ctfd
from jacquard.packs.loader import load_pack

from .conftest import DEMO_PACK


def test_export_demo_pack(tmp_path: Path) -> None:
    issues = export_ctfd(load_pack(DEMO_PACK), tmp_path)
    manifests = sorted(tmp_path.glob("*/*/challenge.yml"))
    assert len(manifests) == 6

    cesar = yaml.safe_load((tmp_path / "crypto" / "cesar" / "challenge.yml").read_text())
    assert cesar["category"] == "Cryptographie"
    assert cesar["type"] == "dynamic"
    assert cesar["extra"] == {"initial": 500, "decay": 10, "minimum": 100}
    assert cesar["flags"] == [
        {"type": "static", "content": "DEMO{jules_serait_fier}", "data": "case_insensitive"}
    ]
    assert cesar["files"] == ["files/message.txt"]
    assert (tmp_path / "crypto" / "cesar" / "files" / "message.txt").is_file()
    assert [h["cost"] for h in cesar["hints"]] == [0, 50]

    ville = yaml.safe_load((tmp_path / "osint" / "ville" / "challenge.yml").read_text())
    assert ville["type"] == "standard" and ville["value"] == 50
    assert ville["flags"][0]["type"] == "regex"

    # Règles non transposables : défi masqué et signalé.
    coffre = yaml.safe_load((tmp_path / "misc" / "coffre" / "challenge.yml").read_text())
    assert coffre["state"] == "hidden"
    assert any(i.startswith("coffre : règle de déblocage non transposable") for i in issues)
    assert any("l'objet « cle-crypto »" in i for i in issues)
    assert any(i.startswith("histoire") for i in issues)
    assert "Limites de l'export" in (tmp_path / "README.md").read_text()


def test_simple_prerequisites_become_requirements(make_pack, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    pack = make_pack()
    manifest = pack / "challenges" / "crypto" / "couches" / "challenge.yml"
    data = yaml.safe_load(manifest.read_text())
    data["unlock"] = {"all": [{"solved": "bienvenue"}, {"solved": "cesar"}]}
    manifest.write_text(yaml.safe_dump(data))
    export_ctfd(load_pack(pack), tmp_path / "out")
    couches = yaml.safe_load(
        (tmp_path / "out" / "crypto" / "couches" / "challenge.yml").read_text()
    )
    assert couches["requirements"] == ["Bienvenue", "Ave César"]
    assert couches["state"] == "visible"


def test_items_are_listed_for_manual_distribution(tmp_path: Path) -> None:
    issues = export_ctfd(load_pack(DEMO_PACK), tmp_path)
    readme = (tmp_path / "README.md").read_text()
    assert "Objets à remettre aux équipes" in readme
    assert "Clé de cryptographie" in readme
    assert any(i.startswith("objets") for i in issues)
