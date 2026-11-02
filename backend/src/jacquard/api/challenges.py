import re
from datetime import timedelta

from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from jacquard.api.deps import AppSettings, ClientIp, CurrentUser, DbSession, Event, Now, api_error
from jacquard.models import Challenge, ChallengeFile, Flag, Solve, Submission, Team, User
from jacquard.packs.schema import EventConfig
from jacquard.security import constant_time_equals, flag_digest, normalize_flag
from jacquard.services import Phase, compute_snapshot, phase, public_cutoff

router = APIRouter(prefix="/api", tags=["challenges"])


class SubmitBody(BaseModel):
    flag: str = Field(min_length=1, max_length=512)


def _can_see_challenges(user: User, event: EventConfig, now: Now) -> bool:
    return user.is_admin or (user.team_id is not None and phase(event, now) != Phase.NOT_STARTED)


def _require_visibility(user: User, event: EventConfig, now: Now) -> None:
    if user.is_admin:
        return
    if user.team_id is None:
        api_error(403, "no_team", "Rejoins ou crée une équipe pour accéder aux défis.")
    if phase(event, now) == Phase.NOT_STARTED:
        api_error(403, "event_not_started", "L'événement n'a pas encore commencé.")


def _get_visible_challenge(
    db: DbSession, user: User, event: EventConfig, now: Now, challenge_id: str
) -> Challenge:
    _require_visibility(user, event, now)
    challenge = db.get(Challenge, challenge_id, options=[selectinload(Challenge.files)])
    if challenge is None or not challenge.active:
        api_error(404, "not_found", "Défi introuvable.")
    return challenge


def _solved_ids(db: DbSession, user: User) -> set[str]:
    if user.team_id is None:
        return set()
    return set(db.scalars(select(Solve.challenge_id).where(Solve.team_id == user.team_id)))


@router.get("/challenges")
def list_challenges(user: CurrentUser, db: DbSession, event: Event, now: Now) -> dict[str, object]:
    current = phase(event, now)
    if not _can_see_challenges(user, event, now):
        return {"phase": current, "challenges": []}
    snapshot = compute_snapshot(db, event, public_cutoff(event, now, user))
    solved = _solved_ids(db, user)
    challenges = db.scalars(
        select(Challenge).where(Challenge.active).order_by(Challenge.position, Challenge.name)
    )
    return {
        "phase": current,
        "challenges": [
            {
                "id": c.id,
                "name": c.name,
                "category": c.category,
                "difficulty": c.difficulty,
                "tags": c.tags,
                "value": snapshot.values.get(c.id, 0),
                "solves": snapshot.solve_counts.get(c.id, 0),
                "solved": c.id in solved,
            }
            for c in challenges
        ],
    }


@router.get("/challenges/{challenge_id}")
def get_challenge(
    challenge_id: str, user: CurrentUser, db: DbSession, event: Event, now: Now
) -> dict[str, object]:
    challenge = _get_visible_challenge(db, user, event, now, challenge_id)
    snapshot = compute_snapshot(db, event, public_cutoff(event, now, user))
    return {
        "id": challenge.id,
        "name": challenge.name,
        "category": challenge.category,
        "difficulty": challenge.difficulty,
        "authors": challenge.authors,
        "tags": challenge.tags,
        "description_html": challenge.description_html,
        "connection": challenge.connection,
        "value": snapshot.values.get(challenge.id, 0),
        "solves": snapshot.solve_counts.get(challenge.id, 0),
        "solved": challenge.id in _solved_ids(db, user),
        "files": [
            {"id": f.id, "name": f.filename, "size": f.size}
            for f in sorted(challenge.files, key=lambda f: f.filename)
        ],
    }


def _matches(flags: list[Flag], provided: str, secret: str) -> bool:
    matched = False
    for flag in flags:
        if flag.kind == "static":
            candidate = flag_digest(secret, provided, flag.case_sensitive)
            # Pas de sortie anticipée : le temps de réponse ne dépend pas du flag trouvé.
            matched |= constant_time_equals(candidate, flag.value)
        elif flag.kind == "regex":
            options = 0 if flag.case_sensitive else re.IGNORECASE
            matched |= re.fullmatch(flag.value, normalize_flag(provided, True), options) is not None
    return matched


@router.post("/challenges/{challenge_id}/submit")
def submit_flag(
    challenge_id: str,
    body: SubmitBody,
    user: CurrentUser,
    db: DbSession,
    event: Event,
    now: Now,
    ip: ClientIp,
    settings: AppSettings,
) -> dict[str, object]:
    if user.team_id is None:
        api_error(403, "no_team", "Rejoins ou crée une équipe pour soumettre un flag.")
    current = phase(event, now)
    if current != Phase.RUNNING:
        message = (
            "L'événement n'a pas encore commencé."
            if current == Phase.NOT_STARTED
            else "L'événement est terminé."
        )
        api_error(403, f"event_{current}", message)

    # Verrou par équipe : les soumissions d'une même équipe sont traitées l'une après
    # l'autre, ce qui rend la limite de tentatives et la détection de doublon fiables.
    db.execute(select(Team.id).where(Team.id == user.team_id).with_for_update())
    challenge = db.get(Challenge, challenge_id, options=[selectinload(Challenge.flags)])
    if challenge is None or not challenge.active:
        api_error(404, "not_found", "Défi introuvable.")

    already = db.scalar(
        select(Solve.id).where(Solve.team_id == user.team_id, Solve.challenge_id == challenge.id)
    )
    if already is not None:
        return {"status": "already_solved"}

    limit = event.submissions.rate_limit
    window_start = now - timedelta(seconds=limit.per_seconds)
    recent = list(
        db.scalars(
            select(Submission.created_at)
            .where(
                Submission.team_id == user.team_id,
                Submission.challenge_id == challenge.id,
                Submission.created_at > window_start,
            )
            .order_by(Submission.created_at)
        )
    )
    if len(recent) >= limit.max:
        retry_after = max(
            1, int((recent[0] + timedelta(seconds=limit.per_seconds) - now).total_seconds()) + 1
        )
        api_error(
            429,
            "rate_limited",
            "Trop de tentatives sur ce défi, patiente un peu.",
            retry_after=retry_after,
        )

    correct = _matches(challenge.flags, body.flag, settings.secret_key.get_secret_value())
    db.add(
        Submission(
            team_id=user.team_id,
            user_id=user.id,
            challenge_id=challenge.id,
            provided=body.flag[:512],
            correct=correct,
            ip=ip[:64],
            created_at=now,
        )
    )
    if not correct:
        return {"status": "incorrect"}

    db.add(Solve(team_id=user.team_id, challenge_id=challenge.id, user_id=user.id, created_at=now))
    try:
        db.flush()
    except IntegrityError:  # pragma: no cover - protégé par le verrou ci-dessus
        db.rollback()
        return {"status": "already_solved"}
    return {"status": "correct"}


@router.get("/files/{file_id}")
def download_file(
    file_id: str, user: CurrentUser, db: DbSession, event: Event, now: Now, settings: AppSettings
) -> FileResponse:
    record = db.get(ChallengeFile, file_id)
    # 404 dans tous les cas d'accès refusé, pour ne pas confirmer l'existence du fichier.
    if record is None or not _can_see_challenges(user, event, now):
        api_error(404, "not_found", "Fichier introuvable.")
    challenge = db.get(Challenge, record.challenge_id)
    if challenge is None or not challenge.active:
        api_error(404, "not_found", "Fichier introuvable.")
    path = settings.files_dir / record.sha256
    if not path.is_file():
        api_error(404, "not_found", "Fichier introuvable.")
    return FileResponse(
        path,
        filename=record.filename,
        media_type="application/octet-stream",
        content_disposition_type="attachment",
    )
