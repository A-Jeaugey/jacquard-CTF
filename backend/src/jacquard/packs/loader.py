"""Chargement et validation d'un pack d'événement depuis le disque.

Le chargeur ne lit que ce que le pack déclare : `event.yml`, les `challenge.yml`, leurs
descriptions et les fichiers listés dans `files`. Les dossiers `solution/` et `src/` ne
sont jamais lus.
"""

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ValidationError

from jacquard.packs.schema import ChallengeConfig, EventConfig

MAX_FILE_SIZE = 200 * 1024 * 1024


@dataclass(frozen=True)
class PackIssue:
    location: str
    message: str

    def __str__(self) -> str:
        return f"{self.location} : {self.message}"


class PackError(Exception):
    def __init__(self, errors: list[PackIssue]) -> None:
        super().__init__(f"{len(errors)} erreur(s) dans le pack")
        self.errors = errors


@dataclass(frozen=True)
class PackFile:
    name: str
    path: Path
    sha256: str
    size: int


@dataclass(frozen=True)
class LoadedChallenge:
    config: ChallengeConfig
    directory: Path
    description_md: str
    files: list[PackFile]


@dataclass
class Pack:
    root: Path
    event: EventConfig
    challenges: list[LoadedChallenge]
    digest: str
    warnings: list[PackIssue] = field(default_factory=list)


def _relative(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _read_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _validation_issues(location: str, exc: ValidationError) -> list[PackIssue]:
    issues = []
    for error in exc.errors():
        where = ".".join(str(part) for part in error["loc"])
        message = error["msg"]
        if error["type"] == "extra_forbidden":
            message = "champ inconnu ou non pris en charge par cette version"
        issues.append(PackIssue(f"{location} [{where}]" if where else location, message))
    return issues


def _parse[M: BaseModel](
    model: type[M], root: Path, path: Path, errors: list[PackIssue]
) -> M | None:
    location = _relative(root, path)
    try:
        data = _read_yaml(path)
    except yaml.YAMLError as exc:
        errors.append(PackIssue(location, f"YAML invalide : {exc}"))
        return None
    if not isinstance(data, dict):
        errors.append(PackIssue(location, "le fichier doit contenir un objet YAML"))
        return None
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        errors.extend(_validation_issues(location, exc))
        return None


def _safe_child(root: Path, base: Path, relative: str) -> Path | None:
    """Résout `relative` depuis `base` et vérifie qu'il reste dans le pack."""
    candidate = (base / relative).resolve()
    if not candidate.is_relative_to(root):
        return None
    return candidate


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_challenge(
    root: Path,
    manifest: Path,
    event: EventConfig,
    errors: list[PackIssue],
    warnings: list[PackIssue],
) -> LoadedChallenge | None:
    config = _parse(ChallengeConfig, root, manifest, errors)
    if config is None:
        return None
    location = _relative(root, manifest)
    directory = manifest.parent
    ok = True

    if config.category not in {c.id for c in event.categories}:
        errors.append(PackIssue(location, f"catégorie inconnue : {config.category}"))
        ok = False
    if config.difficulty is not None and config.difficulty not in event.difficulties:
        errors.append(
            PackIssue(location, f"difficulté non déclarée dans event.yml : {config.difficulty}")
        )
        ok = False

    description_path = _safe_child(root, directory, config.description)
    description_md = ""
    if description_path is None:
        errors.append(PackIssue(location, "la description doit se trouver dans le pack"))
        ok = False
    elif not description_path.is_file():
        errors.append(PackIssue(location, f"description introuvable : {config.description}"))
        ok = False
    else:
        description_md = description_path.read_text(encoding="utf-8")

    files: list[PackFile] = []
    names: set[str] = set()
    for entry in config.files:
        path = _safe_child(root, directory, entry)
        if path is None:
            errors.append(PackIssue(location, f"fichier hors du pack : {entry}"))
            ok = False
            continue
        if not path.is_file():
            errors.append(PackIssue(location, f"fichier introuvable : {entry}"))
            ok = False
            continue
        if "solution" in path.relative_to(root).parts:
            errors.append(
                PackIssue(location, f"un fichier de solution ne peut pas être distribué : {entry}")
            )
            ok = False
            continue
        size = path.stat().st_size
        if size > MAX_FILE_SIZE:
            errors.append(PackIssue(location, f"fichier trop volumineux (> 200 Mo) : {entry}"))
            ok = False
            continue
        if path.name in names:
            errors.append(PackIssue(location, f"deux fichiers portent le même nom : {path.name}"))
            ok = False
            continue
        names.add(path.name)
        files.append(PackFile(name=path.name, path=path, sha256=_sha256(path), size=size))

    prefix = event.flag_prefix
    if prefix:
        for flag in config.flags:
            if flag.type == "static" and not flag.value.startswith(prefix):
                warnings.append(
                    PackIssue(location, f"un flag ne respecte pas le format {event.flag_format}")
                )

    if not ok:
        return None
    return LoadedChallenge(
        config=config, directory=directory, description_md=description_md, files=files
    )


def load_pack(path: Path) -> Pack:
    """Charge et valide un pack. Lève `PackError` avec la liste complète des erreurs."""
    root = path.resolve()
    errors: list[PackIssue] = []
    warnings: list[PackIssue] = []

    event_path = root / "event.yml"
    if not event_path.is_file():
        raise PackError([PackIssue(_relative(root, event_path), "fichier introuvable")])
    event = _parse(EventConfig, root, event_path, errors)
    if event is None:
        raise PackError(errors)

    challenges: list[LoadedChallenge] = []
    seen: dict[str, str] = {}
    challenges_dir = root / "challenges"
    manifests = sorted(challenges_dir.rglob("challenge.yml")) if challenges_dir.is_dir() else []
    for manifest in manifests:
        if "solution" in manifest.relative_to(challenges_dir).parts:
            continue
        loaded = _load_challenge(root, manifest, event, errors, warnings)
        if loaded is None:
            continue
        location = _relative(root, manifest)
        if loaded.config.id in seen:
            errors.append(
                PackIssue(
                    location, f"id déjà utilisé par {seen[loaded.config.id]} : {loaded.config.id}"
                )
            )
            continue
        seen[loaded.config.id] = location
        challenges.append(loaded)

    if not manifests:
        warnings.append(PackIssue("challenges/", "aucun défi trouvé"))
    if errors:
        raise PackError(errors)

    return Pack(
        root=root,
        event=event,
        challenges=challenges,
        digest=_pack_digest(event, challenges),
        warnings=warnings,
    )


def _pack_digest(event: EventConfig, challenges: list[LoadedChallenge]) -> str:
    digest = hashlib.sha256(event.model_dump_json().encode())
    for challenge in sorted(challenges, key=lambda c: c.config.id):
        digest.update(challenge.config.model_dump_json().encode())
        digest.update(challenge.description_md.encode())
        for pack_file in challenge.files:
            digest.update(pack_file.sha256.encode())
    return digest.hexdigest()
