"""Import d'un pack validé dans la base.

L'import est idempotent et ne supprime jamais de résolution : un défi retiré du pack est
simplement désactivé. Il peut donc être relancé pendant l'événement pour corriger une
coquille.
"""

import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from jacquard.markdown import render_markdown
from jacquard.models import Challenge, ChallengeFile, EventRow, Flag, Hint, StoryEntry
from jacquard.packs.loader import LoadedChallenge, Pack
from jacquard.packs.schema import GrantItem, dump_rule
from jacquard.security import flag_digest


@dataclass
class SyncReport:
    created: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    deactivated: list[str] = field(default_factory=list)
    event_changed: bool = False
    story_created: list[str] = field(default_factory=list)
    story_updated: list[str] = field(default_factory=list)
    story_deactivated: list[str] = field(default_factory=list)


def _store_file(files_dir: Path, sha256: str, source: Path) -> None:
    files_dir.mkdir(parents=True, exist_ok=True)
    target = files_dir / sha256
    if not target.exists():
        temporary = files_dir / f".{sha256}.{uuid.uuid4().hex}.tmp"
        shutil.copyfile(source, temporary)
        temporary.replace(target)


def _flag_rows(loaded: LoadedChallenge, secret: str) -> list[Flag]:
    rows = []
    for spec in loaded.config.flags:
        if spec.type == "static":
            value = flag_digest(secret, spec.value, spec.case_sensitive)
        else:
            value = spec.pattern
        rows.append(Flag(kind=spec.type, value=value, case_sensitive=spec.case_sensitive))
    return rows


def _on_solve(loaded: LoadedChallenge) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    for action in loaded.config.on_solve:
        if isinstance(action, GrantItem):
            actions.append({"grant_item": action.grant_item})
        else:
            actions.append({"notify_html": render_markdown(action.notify)})
    return actions


def _hint_state(hints: dict[str, Hint], challenge_id: str) -> tuple[object, ...]:
    return tuple(
        sorted(
            (h.id, h.position, h.text_html, h.cost, repr(h.available))
            for h in hints.values()
            if h.challenge_id == challenge_id and h.active
        )
    )


def _fingerprint(challenge: Challenge) -> tuple[object, ...]:
    return (
        repr(challenge.unlock),
        challenge.when_locked,
        challenge.locked_message,
        repr(challenge.on_solve),
        challenge.name,
        challenge.category,
        challenge.difficulty,
        tuple(challenge.authors),
        tuple(challenge.tags),
        challenge.description_html,
        tuple(sorted(challenge.scoring.items())),
        challenge.connection,
        challenge.position,
        challenge.active,
        tuple(sorted((f.kind, f.value, f.case_sensitive) for f in challenge.flags)),
        tuple(sorted((f.filename, f.sha256) for f in challenge.files)),
    )


def sync_pack(
    session: Session,
    pack: Pack,
    *,
    secret: str,
    files_dir: Path,
    now: datetime,
    dry_run: bool = False,
) -> SyncReport:
    report = SyncReport()
    event_config = pack.event.model_dump(mode="json")

    event = session.get(EventRow, 1)
    if event is None:
        event = EventRow(
            id=1, slug=pack.event.id, config=event_config, pack_digest="", synced_at=now
        )
        session.add(event)
        report.event_changed = True
    elif event.config != event_config or event.slug != pack.event.id:
        report.event_changed = True
        event.config = event_config
        event.slug = pack.event.id
    event.pack_digest = pack.digest
    event.synced_at = now

    existing = {
        c.id: c
        for c in session.scalars(
            select(Challenge).options(selectinload(Challenge.flags), selectinload(Challenge.files))
        )
    }
    default_scoring = pack.event.scoring.default
    hints = {h.id: h for h in session.scalars(select(Hint))}
    seen_hints: set[str] = set()

    for loaded in pack.challenges:
        config = loaded.config
        challenge = existing.pop(config.id, None)
        is_new = challenge is None
        if challenge is None:
            challenge = Challenge(id=config.id)
            session.add(challenge)
        before = None if is_new else (_fingerprint(challenge), _hint_state(hints, config.id))

        challenge.name = config.name
        challenge.category = config.category
        challenge.difficulty = config.difficulty
        challenge.authors = list(config.authors)
        challenge.tags = list(config.tags)
        challenge.description_html = render_markdown(loaded.description_md)
        challenge.scoring = (config.scoring or default_scoring).model_dump(mode="json")
        challenge.connection = (
            config.connection.replace("{challenge_host}", pack.event.challenge_host or "")
            if config.connection
            else None
        )
        challenge.position = config.position
        challenge.active = True
        challenge.unlock = dump_rule(config.unlock)
        challenge.when_locked = config.when_locked
        challenge.locked_message = config.locked_message
        challenge.on_solve = _on_solve(loaded)

        for position, spec in enumerate(config.hints):
            seen_hints.add(spec.id)
            hint = hints.get(spec.id)
            if hint is None:
                hint = Hint(id=spec.id)
                session.add(hint)
                hints[spec.id] = hint
            hint.challenge_id = config.id
            hint.position = position
            hint.text_html = render_markdown(spec.text)
            hint.cost = spec.cost
            hint.available = dump_rule(spec.available)
            hint.active = True
        for hint in hints.values():
            if hint.challenge_id == config.id and hint.id not in seen_hints:
                hint.active = False

        new_flags = _flag_rows(loaded, secret)
        current_flags = sorted((f.kind, f.value, f.case_sensitive) for f in challenge.flags)
        if current_flags != sorted((f.kind, f.value, f.case_sensitive) for f in new_flags):
            challenge.flags = new_flags

        current_files = {(f.filename, f.sha256): f for f in challenge.files}
        wanted = {(f.name, f.sha256) for f in loaded.files}
        if set(current_files) != wanted:
            kept = [f for key, f in current_files.items() if key in wanted]
            added = [
                ChallengeFile(id=uuid.uuid4().hex, filename=f.name, sha256=f.sha256, size=f.size)
                for f in loaded.files
                if (f.name, f.sha256) not in current_files
            ]
            challenge.files = kept + added
        if not dry_run:
            for pack_file in loaded.files:
                _store_file(files_dir, pack_file.sha256, pack_file.path)

        if is_new:
            report.created.append(config.id)
        elif before != (_fingerprint(challenge), _hint_state(hints, config.id)):
            report.updated.append(config.id)
        else:
            report.unchanged.append(config.id)

    for challenge in existing.values():
        if challenge.active:
            challenge.active = False
            report.deactivated.append(challenge.id)
    for hint in hints.values():
        if hint.id not in seen_hints:
            hint.active = False

    _sync_story(session, pack, report)

    if dry_run:
        session.rollback()
    else:
        session.commit()
    return report


def _sync_story(session: Session, pack: Pack, report: SyncReport) -> None:
    entries = {e.id: e for e in session.scalars(select(StoryEntry))}
    for chapter in pack.story:
        config = chapter.config
        values = {
            "title": config.title,
            "position": config.order,
            "body_html": render_markdown(chapter.body_md),
            "unlock": dump_rule(config.unlock),
            "public": config.public,
            "active": True,
        }
        entry = entries.pop(config.id, None)
        if entry is None:
            session.add(StoryEntry(id=config.id, **values))
            report.story_created.append(config.id)
        elif any(getattr(entry, key) != value for key, value in values.items()):
            for key, value in values.items():
                setattr(entry, key, value)
            report.story_updated.append(config.id)
    for entry in entries.values():
        if entry.active:
            entry.active = False
            report.story_deactivated.append(entry.id)
