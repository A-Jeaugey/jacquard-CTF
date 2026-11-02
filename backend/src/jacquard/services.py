"""Logique métier partagée entre les routes : état de l'événement, scores."""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.orm import Session

from jacquard.models import Challenge, EventRow, Solve, Team, User
from jacquard.packs.schema import EventConfig
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
    if cutoff is not None:
        query = query.where(Solve.created_at < cutoff)
    solves = [SolveRecord(*row) for row in session.execute(query)]
    teams = [TeamRecord(*row) for row in session.execute(select(Team.id, Team.name, Team.hidden))]
    return compute_scores(challenges, solves, teams, event.scoring.first_blood)
