"""Chargement et validation d'un pack d'événement depuis le disque.

Le chargeur ne lit que ce que le pack déclare : `event.yml`, les `challenge.yml`, leurs
descriptions, les fichiers listés dans `files` et les chapitres de `story/`. Les dossiers
`solution/` et `src/` ne sont jamais lus.

Au-delà du format de chaque fichier, il vérifie la cohérence de l'ensemble : références
entre défis, objets et indices, et absence de défi impossible à débloquer.
"""

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ValidationError

from jacquard.packs.schema import (
    ChallengeConfig,
    DynamicScoring,
    EventConfig,
    GrantItem,
    Rule,
    StoryConfig,
)
from jacquard.rules import ChallengeMeta, Unlockable, possible, reachable, references

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


@dataclass(frozen=True)
class LoadedStory:
    config: StoryConfig
    body_md: str


@dataclass
class Pack:
    root: Path
    event: EventConfig
    challenges: list[LoadedChallenge]
    digest: str
    story: list[LoadedStory] = field(default_factory=list)
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
    model: type[M], root: Path, path: Path, errors: list[PackIssue], text: str | None = None
) -> M | None:
    location = _relative(root, path)
    try:
        data = yaml.safe_load(text) if text is not None else _read_yaml(path)
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


def _load_story(root: Path, path: Path, errors: list[PackIssue]) -> LoadedStory | None:
    """Un chapitre est un fichier Markdown précédé d'un en-tête YAML entre deux `---`."""
    location = _relative(root, path)
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        errors.append(
            PackIssue(location, "en-tête YAML manquant (le fichier doit commencer par ---)")
        )
        return None
    try:
        end = next(i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration:
        errors.append(PackIssue(location, "en-tête YAML non fermé (--- manquant)"))
        return None
    config = _parse(StoryConfig, root, path, errors, text="".join(lines[1:end]))
    if config is None:
        return None
    return LoadedStory(config=config, body_md="".join(lines[end + 1 :]).strip() + "\n")


def _max_points(config: ChallengeConfig, event: EventConfig) -> int:
    scoring = config.scoring or event.scoring.default
    base = scoring.initial if isinstance(scoring, DynamicScoring) else scoring.value
    return base + max(event.scoring.first_blood, default=0)


def _check_consistency(
    event: EventConfig,
    challenges: list[LoadedChallenge],
    story: list[LoadedStory],
    root: Path,
    errors: list[PackIssue],
    warnings: list[PackIssue],
) -> None:
    challenge_ids = {c.config.id for c in challenges}
    category_ids = {c.id for c in event.categories}
    item_ids = {i.id for i in event.items}
    hint_owner: dict[str, str] = {}
    for challenge in challenges:
        for hint in challenge.config.hints:
            if hint.id in hint_owner:
                errors.append(
                    PackIssue(
                        _relative(root, challenge.directory / "challenge.yml"),
                        f"id d'indice déjà utilisé par le défi {hint_owner[hint.id]} : {hint.id}",
                    )
                )
            hint_owner.setdefault(hint.id, challenge.config.id)

    def check_rule(location: str, rule: Rule | None) -> None:
        found = references(rule)
        for kind, unknown in (
            ("défi", found.challenges - challenge_ids),
            ("catégorie", found.categories - category_ids),
            ("difficulté", found.difficulties - set(event.difficulties)),
            ("objet", found.items - item_ids),
            ("indice", found.hints - set(hint_owner)),
        ):
            for identifier in sorted(unknown):
                errors.append(
                    PackIssue(location, f"la règle mentionne un {kind} inconnu : {identifier}")
                )

    granted: set[str] = set()
    for challenge in challenges:
        location = _relative(root, challenge.directory / "challenge.yml")
        config = challenge.config
        check_rule(f"{location} [unlock]", config.unlock)
        for hint in config.hints:
            check_rule(f"{location} [hints.{hint.id}.available]", hint.available)
        for action in config.on_solve:
            if isinstance(action, GrantItem):
                if action.grant_item not in item_ids:
                    errors.append(
                        PackIssue(
                            location, f"objet non déclaré dans event.yml : {action.grant_item}"
                        )
                    )
                granted.add(action.grant_item)
        if config.locked_message and config.when_locked == "hidden":
            warnings.append(
                PackIssue(location, "locked_message n'est affiché qu'avec when_locked: teaser")
            )

    for item in sorted(item_ids - granted):
        warnings.append(PackIssue("event.yml", f"l'objet {item} n'est accordé par aucun défi"))

    story_ids: dict[str, str] = {}
    for chapter in story:
        location = f"story/{chapter.config.id}"
        if chapter.config.id in story_ids:
            errors.append(PackIssue(location, f"id de chapitre déjà utilisé : {chapter.config.id}"))
        story_ids[chapter.config.id] = location
        check_rule(f"{location} [unlock]", chapter.config.unlock)

    if errors:
        return

    catalog = {
        c.config.id: ChallengeMeta(
            category=c.config.category,
            tags=frozenset(c.config.tags),
            difficulty=c.config.difficulty,
        )
        for c in challenges
    }
    best_case = reachable(
        [
            Unlockable(
                id=c.config.id,
                unlock=c.config.unlock,
                max_points=_max_points(c.config, event),
                grants=frozenset(
                    a.grant_item for a in c.config.on_solve if isinstance(a, GrantItem)
                ),
                hints={h.id: h.available for h in c.config.hints},
            )
            for c in challenges
        ],
        catalog,
        start=event.schedule.start,
        end=event.schedule.end,
        tz=event.tz,
    )
    for challenge in challenges:
        if challenge.config.id not in best_case.solved:
            errors.append(
                PackIssue(
                    _relative(root, challenge.directory / "challenge.yml"),
                    "défi impossible à débloquer (dépendance circulaire ou condition irréalisable)",
                )
            )
    for chapter in story:
        if not possible(chapter.config.unlock, best_case):
            warnings.append(
                PackIssue(f"story/{chapter.config.id}", "chapitre impossible à débloquer")
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

    story: list[LoadedStory] = []
    story_dir = root / "story"
    if story_dir.is_dir():
        for chapter_path in sorted(story_dir.glob("*.md")):
            chapter = _load_story(root, chapter_path, errors)
            if chapter is not None:
                story.append(chapter)

    if not errors:
        _check_consistency(event, challenges, story, root, errors, warnings)
    if errors:
        raise PackError(errors)

    return Pack(
        root=root,
        event=event,
        challenges=challenges,
        story=story,
        digest=_pack_digest(event, challenges, story),
        warnings=warnings,
    )


def _pack_digest(
    event: EventConfig, challenges: list[LoadedChallenge], story: list[LoadedStory]
) -> str:
    digest = hashlib.sha256(event.model_dump_json().encode())
    for challenge in sorted(challenges, key=lambda c: c.config.id):
        digest.update(challenge.config.model_dump_json().encode())
        digest.update(challenge.description_md.encode())
        for pack_file in challenge.files:
            digest.update(pack_file.sha256.encode())
    for chapter in sorted(story, key=lambda c: c.config.id):
        digest.update(chapter.config.model_dump_json().encode())
        digest.update(chapter.body_md.encode())
    return digest.hexdigest()
