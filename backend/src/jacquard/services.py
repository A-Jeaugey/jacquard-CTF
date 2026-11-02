"""Logique métier partagée entre les routes : état de l'événement, scores, progression."""

import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from functools import lru_cache
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from jacquard.models import (
    Challenge,
    EventRow,
    Hint,
    HintUnlock,
    Solve,
    StoryEntry,
    Team,
    Unlock,
    User,
)
from jacquard.packs.schema import EventConfig, Rule, load_rule
from jacquard.rules import ChallengeMeta, TeamContext, evaluate
from jacquard.scoring import ScoringResult, SolveRecord, TeamRecord, compute_scores

_event_cache: dict[tuple[str, datetime], EventConfig] = {}


class Phase(StrEnum):
    NOT_STARTED = "not_started"
    RUNNING = "running"
    ENDED = "ended"


def load_event(session: Session) -> EventConfig | None:
    row = session.get(EventRow, 1)
    if row is None:
        return None
    key = (row.pack_digest, row.synced_at)
    cached = _event_cache.get(key)
    if cached is None:
        cached = EventConfig.model_validate(row.config)
        _event_cache.clear()
        _event_cache[key] = cached
    return cached


def phase(event: EventConfig, now: datetime) -> Phase:
    if now < event.schedule.start:
        return Phase.NOT_STARTED
    if now >= event.schedule.end:
        return Phase.ENDED
    return Phase.RUNNING


def is_frozen(event: EventConfig, now: datetime) -> bool:
    return event.schedule.freeze is not None and now >= event.schedule.freeze


def public_cutoff(event: EventConfig, now: datetime, viewer: User | None) -> datetime | None:
    """Date au-delà de laquelle les résolutions sont masquées pour ce visiteur (gel)."""
    if viewer is not None and viewer.is_admin:
        return None
    return event.schedule.freeze if is_frozen(event, now) else None


def compute_snapshot(
    session: Session, event: EventConfig, cutoff: datetime | None = None
) -> ScoringResult:
    challenges = {
        c.id: c.scoring for c in session.scalars(select(Challenge).where(Challenge.active))
    }
    query = select(Solve.id, Solve.team_id, Solve.challenge_id, Solve.created_at)
    penalty_query = select(HintUnlock.team_id, func.sum(HintUnlock.cost)).group_by(
        HintUnlock.team_id
    )
    if cutoff is not None:
        query = query.where(Solve.created_at < cutoff)
        penalty_query = penalty_query.where(HintUnlock.created_at < cutoff)
    solves = [SolveRecord(*row) for row in session.execute(query)]
    teams = [TeamRecord(*row) for row in session.execute(select(Team.id, Team.name, Team.hidden))]
    penalties = {team_id: int(total) for team_id, total in session.execute(penalty_query)}
    return compute_scores(challenges, solves, teams, event.scoring.first_blood, penalties)


# --------------------------------------------------------------------------- progression


@lru_cache(maxsize=1024)
def _parse_rule(serialized: str) -> Rule | None:
    return load_rule(json.loads(serialized))


def stored_rule(data: dict[str, Any] | None) -> Rule | None:
    return None if data is None else _parse_rule(json.dumps(data, sort_keys=True))


@dataclass
class TeamProgress:
    """Ce qu'une équipe a résolu, obtenu et débloqué."""

    solved: set[str] = field(default_factory=set)
    items: set[str] = field(default_factory=set)
    hints_used: set[str] = field(default_factory=set)
    challenges: set[str] = field(default_factory=set)
    hints: set[str] = field(default_factory=set)
    story: set[str] = field(default_factory=set)
    # Déblocages obtenus pendant cet appel, par type, pour les notifications.
    new: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))


def team_progress(
    session: Session,
    event: EventConfig,
    team_id: int,
    now: datetime,
    snapshot: ScoringResult | None = None,
) -> TeamProgress:
    """Évalue les règles de déblocage pour l'équipe et enregistre les nouveaux déblocages.

    Les déblocages sont définitifs : une fois enregistré, un défi reste visible même si
    la règle redevient fausse (score qui baisse, condition horaire dépassée...).
    """
    progress = TeamProgress()
    if phase(event, now) == Phase.NOT_STARTED:
        return progress

    challenges = list(session.scalars(select(Challenge).where(Challenge.active)))
    by_id = {c.id: c for c in challenges}
    progress.solved = {
        cid
        for cid in session.scalars(select(Solve.challenge_id).where(Solve.team_id == team_id))
        if cid in by_id
    }
    progress.items = {item for cid in progress.solved for item in by_id[cid].granted_items}
    progress.hints_used = set(
        session.scalars(select(HintUnlock.hint_id).where(HintUnlock.team_id == team_id))
    )
    snapshot = snapshot or compute_snapshot(session, event)
    team_score = snapshot.team(team_id)

    ctx = TeamContext(
        solved=frozenset(progress.solved),
        catalog={
            c.id: ChallengeMeta(c.category, frozenset(c.tags), c.difficulty) for c in challenges
        },
        score=team_score.score if team_score else 0,
        items=frozenset(progress.items),
        hints_used=frozenset(progress.hints_used),
        now=now,
        start=event.schedule.start,
        tz=event.tz,
    )
    acquired = {
        (kind, target)
        for kind, target in session.execute(
            select(Unlock.kind, Unlock.target_id).where(Unlock.team_id == team_id)
        )
    }

    def check(
        kind: str, target: str, rule: dict[str, Any] | None, *, granted: bool = False
    ) -> bool:
        if (kind, target) in acquired:
            return True
        if granted or evaluate(stored_rule(rule), ctx):
            progress.new[kind].append(target)
            return True
        return False

    for challenge in challenges:
        if check(
            "challenge", challenge.id, challenge.unlock, granted=challenge.id in progress.solved
        ):
            progress.challenges.add(challenge.id)

    hints = session.scalars(select(Hint).where(Hint.active))
    for hint in hints:
        if hint.challenge_id in progress.challenges and check("hint", hint.id, hint.available):
            progress.hints.add(hint.id)

    for entry in session.scalars(
        select(StoryEntry).where(StoryEntry.active, StoryEntry.public.is_(False))
    ):
        if check("story", entry.id, entry.unlock):
            progress.story.add(entry.id)

    # Ordre fixe : deux requêtes d'une même équipe qui insèrent les mêmes déblocages dans un
    # ordre différent peuvent s'interbloquer (constaté au test de charge).
    rows = sorted(
        (
            {"team_id": team_id, "kind": kind, "target_id": target, "created_at": now}
            for kind, targets in progress.new.items()
            for target in targets
        ),
        key=lambda row: (row["kind"], row["target_id"]),
    )
    if rows:
        session.execute(insert(Unlock).values(rows).on_conflict_do_nothing())
    return progress


SECRET_CHALLENGE_LABEL = "un défi secret"  # noqa: S105 (libellé, pas un mot de passe)


def public_challenge_name(challenge: Challenge) -> str:
    """Nom affichable publiquement (fil d'actualité, notifications aux autres équipes).

    Un défi caché tant qu'il est verrouillé ne doit pas révéler son existence aux équipes
    qui ne l'ont pas encore débloqué."""
    if challenge.unlock is not None and challenge.when_locked == "hidden":
        return SECRET_CHALLENGE_LABEL
    return challenge.name
