import re
from datetime import timedelta

from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from jacquard.api.deps import (
    AppSettings,
    ClientIp,
    CurrentUser,
    DbSession,
    Event,
    Now,
    api_error,
)
from jacquard.api.routing import CommittingRoute
from jacquard.models import (
    Challenge,
    ChallengeFile,
    Flag,
    Hint,
    HintUnlock,
    Solve,
    StoryEntry,
    Submission,
    Team,
    User,
)
from jacquard.packs.schema import EventConfig
from jacquard.realtime import publish
from jacquard.security import constant_time_equals, flag_digest, normalize_flag
from jacquard.services import (
    Phase,
    TeamProgress,
    compute_snapshot,
    is_frozen,
    phase,
    public_challenge_name,
    public_cutoff,
    team_progress,
)

router = APIRouter(prefix="/api", tags=["challenges"], route_class=CommittingRoute)


class SubmitBody(BaseModel):
    flag: str = Field(min_length=1, max_length=512)


# --------------------------------------------------------------------------- accès


def _require_access(user: User, event: EventConfig, now: Now) -> None:
    if user.is_admin:
        return
    if user.team_id is None:
        api_error(403, "no_team", "Rejoins ou crée une équipe pour accéder aux défis.")
    if phase(event, now) == Phase.NOT_STARTED:
        api_error(403, "event_not_started", "L'événement n'a pas encore commencé.")


def _progress(db: DbSession, user: User, event: EventConfig, now: Now) -> TeamProgress | None:
    """Progression de l'équipe du joueur ; `None` pour un admin (accès complet)."""
    if user.is_admin or user.team_id is None:
        return None
    return team_progress(db, event, user.team_id, now)


def _accessible_challenge(
    db: DbSession, challenge_id: str, progress: TeamProgress | None
) -> Challenge:
    """Défi actif et débloqué. Verrouillé : 403 s'il est annoncé (teaser), sinon 404 pour
    ne pas confirmer son existence."""
    challenge = db.get(Challenge, challenge_id)
    if challenge is None or not challenge.active:
        api_error(404, "not_found", "Défi introuvable.")
    if progress is not None and challenge.id not in progress.challenges:
        if challenge.when_locked == "teaser":
            api_error(403, "locked", challenge.locked_message or "Ce défi est encore verrouillé.")
        api_error(404, "not_found", "Défi introuvable.")
    return challenge


# --------------------------------------------------------------------------- lecture


@router.get("/challenges")
def list_challenges(user: CurrentUser, db: DbSession, event: Event, now: Now) -> dict[str, object]:
    current = phase(event, now)
    if not user.is_admin and (user.team_id is None or current == Phase.NOT_STARTED):
        return {"phase": current, "challenges": []}
    progress = _progress(db, user, event, now)
    snapshot = compute_snapshot(db, event, public_cutoff(event, now, user))
    challenges = db.scalars(
        select(Challenge).where(Challenge.active).order_by(Challenge.position, Challenge.name)
    )
    items: list[dict[str, object]] = []
    for c in challenges:
        unlocked = progress is None or c.id in progress.challenges
        if not unlocked and c.when_locked != "teaser":
            continue
        entry: dict[str, object] = {
            "id": c.id,
            "name": c.name,
            "category": c.category,
            "difficulty": c.difficulty,
            "tags": c.tags,
            "value": snapshot.values.get(c.id, 0),
            "solves": snapshot.solve_counts.get(c.id, 0),
            "solved": progress is not None and c.id in progress.solved,
            "locked": not unlocked,
            "locked_message": None if unlocked else c.locked_message,
        }
        if user.is_admin:
            entry["unlock"] = c.unlock
        items.append(entry)
    return {"phase": current, "challenges": items}


def _hint_views(
    db: DbSession, challenge: Challenge, progress: TeamProgress | None
) -> list[dict[str, object]]:
    hints = db.scalars(
        select(Hint).where(Hint.challenge_id == challenge.id, Hint.active).order_by(Hint.position)
    )
    views = []
    for hint in hints:
        purchased = progress is not None and hint.id in progress.hints_used
        visible = progress is None or purchased
        views.append(
            {
                "id": hint.id,
                "cost": hint.cost,
                "available": progress is None or hint.id in progress.hints,
                "unlocked": purchased,
                "text_html": hint.text_html if visible else None,
            }
        )
    return views


@router.get("/challenges/{challenge_id}")
def get_challenge(
    challenge_id: str, user: CurrentUser, db: DbSession, event: Event, now: Now
) -> dict[str, object]:
    _require_access(user, event, now)
    progress = _progress(db, user, event, now)
    challenge = _accessible_challenge(db, challenge_id, progress)
    snapshot = compute_snapshot(db, event, public_cutoff(event, now, user))
    files = db.scalars(
        select(ChallengeFile)
        .where(ChallengeFile.challenge_id == challenge.id)
        .order_by(ChallengeFile.filename)
    )
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
        "solved": progress is not None and challenge.id in progress.solved,
        "locked": False,
        "locked_message": None,
        "files": [{"id": f.id, "name": f.filename, "size": f.size} for f in files],
        "hints": _hint_views(db, challenge, progress),
    }


# --------------------------------------------------------------------------- écriture


def _require_running(event: EventConfig, now: Now) -> None:
    current = phase(event, now)
    if current != Phase.RUNNING:
        message = (
            "L'événement n'a pas encore commencé."
            if current == Phase.NOT_STARTED
            else "L'événement est terminé."
        )
        api_error(403, f"event_{current}", message)


def _require_player(user: User) -> int:
    if user.team_id is None:
        api_error(403, "no_team", "Rejoins ou crée une équipe pour participer.")
    return user.team_id


def _lock_team(db: DbSession, team_id: int) -> Team:
    # Verrou par équipe : les actions d'une même équipe sont traitées l'une après l'autre,
    # ce qui rend fiables la limite de tentatives, les doublons et les achats d'indices.
    team = db.scalar(select(Team).where(Team.id == team_id).with_for_update())
    assert team is not None
    return team


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


def _unlock_summary(db: DbSession, progress: TeamProgress) -> dict[str, list[dict[str, str]]]:
    """Nouveaux défis et chapitres débloqués, avec leurs noms, pour l'affichage."""
    challenge_ids = [c for c in progress.new.get("challenge", []) if c not in progress.solved]
    story_ids = progress.new.get("story", [])
    challenges = (
        list(
            db.execute(select(Challenge.id, Challenge.name).where(Challenge.id.in_(challenge_ids)))
        )
        if challenge_ids
        else []
    )
    chapters = (
        list(
            db.execute(select(StoryEntry.id, StoryEntry.title).where(StoryEntry.id.in_(story_ids)))
        )
        if story_ids
        else []
    )
    return {
        "challenges": [{"id": cid, "name": name} for cid, name in challenges],
        "story": [{"id": sid, "title": title} for sid, title in chapters],
    }


def _publish_unlocks(db: DbSession, team_id: int, summary: dict[str, list[dict[str, str]]]) -> None:
    if summary["challenges"] or summary["story"]:
        publish(db, "unlock", summary, teams=[team_id], admin=False)


def _first_blood_rank(
    db: DbSession, event: EventConfig, challenge_id: str, team: Team
) -> int | None:
    if team.hidden or not event.scoring.first_blood:
        return None
    rank = db.scalar(
        select(func.count())
        .select_from(Solve)
        .join(Team, Team.id == Solve.team_id)
        .where(Solve.challenge_id == challenge_id, Team.hidden.is_(False))
    )
    return rank if rank and rank <= len(event.scoring.first_blood) else None


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
    team_id = _require_player(user)
    _require_running(event, now)
    team = _lock_team(db, team_id)
    progress = team_progress(db, event, team_id, now)
    challenge = _accessible_challenge(db, challenge_id, progress)

    if challenge.id in progress.solved:
        return {"status": "already_solved"}

    limit = event.submissions.rate_limit
    window_start = now - timedelta(seconds=limit.per_seconds)
    recent = list(
        db.scalars(
            select(Submission.created_at)
            .where(
                Submission.team_id == team_id,
                Submission.challenge_id == challenge.id,
                Submission.created_at > window_start,
            )
            .order_by(Submission.created_at)
        )
    )
    if len(recent) >= limit.max:
        reset = recent[0] + timedelta(seconds=limit.per_seconds)
        api_error(
            429,
            "rate_limited",
            "Trop de tentatives sur ce défi, patiente un peu.",
            retry_after=max(1, int((reset - now).total_seconds()) + 1),
        )

    flags = list(db.scalars(select(Flag).where(Flag.challenge_id == challenge.id)))
    correct = _matches(flags, body.flag, settings.secret_key.get_secret_value())
    db.add(
        Submission(
            team_id=team_id,
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

    db.add(Solve(team_id=team_id, challenge_id=challenge.id, user_id=user.id, created_at=now))
    try:
        db.flush()
    except IntegrityError:  # pragma: no cover - protégé par le verrou d'équipe
        db.rollback()
        return {"status": "already_solved"}

    first_blood = _first_blood_rank(db, event, challenge.id, team)
    unlocked = _unlock_summary(db, team_progress(db, event, team_id, now))
    catalog = {i.id: i for i in event.items}
    items = [
        {"id": i.id, "name": i.name, "description": i.description}
        for i in (catalog.get(item_id) for item_id in challenge.granted_items)
        if i is not None
    ]
    notifications = [a["notify_html"] for a in challenge.on_solve if "notify_html" in a]

    # Pendant le gel, seules l'équipe concernée et l'orga sont prévenues.
    # Les autres équipes reçoivent cet événement : on ne révèle ni l'identifiant ni le nom
    # d'un défi caché qu'elles n'ont peut-être pas encore débloqué.
    secret = public_challenge_name(challenge) != challenge.name
    publish(
        db,
        "solve",
        {
            "team_id": team_id,
            "team": team.name,
            "challenge_id": None if secret else challenge.id,
            "challenge": public_challenge_name(challenge),
            "first_blood": first_blood,
        },
        public=not team.hidden and not is_frozen(event, now),
        teams=[team_id],
    )
    publish(
        db,
        "team_update",
        {"reason": "solve", "user": user.username, "challenge": challenge.name},
        teams=[team_id],
        admin=False,
    )
    _publish_unlocks(db, team_id, unlocked)
    return {
        "status": "correct",
        "first_blood": first_blood,
        "notifications": notifications,
        "items": items,
        "unlocked": unlocked,
    }


@router.post("/challenges/{challenge_id}/hints/{hint_id}/unlock")
def unlock_hint(
    challenge_id: str,
    hint_id: str,
    user: CurrentUser,
    db: DbSession,
    event: Event,
    now: Now,
) -> dict[str, object]:
    team_id = _require_player(user)
    _require_running(event, now)
    _lock_team(db, team_id)
    progress = team_progress(db, event, team_id, now)
    challenge = _accessible_challenge(db, challenge_id, progress)
    hint = db.get(Hint, hint_id)
    if hint is None or not hint.active or hint.challenge_id != challenge.id:
        api_error(404, "not_found", "Indice introuvable.")
    if hint.id in progress.hints_used:
        return {"id": hint.id, "cost": hint.cost, "text_html": hint.text_html}
    if hint.id not in progress.hints:
        api_error(403, "hint_unavailable", "Cet indice n'est pas encore disponible.")
    if event.hints.require_points and hint.cost > 0:
        score = compute_snapshot(db, event).team(team_id)
        if score is None or score.score < hint.cost:
            api_error(
                403, "not_enough_points", "Ton équipe n'a pas assez de points pour cet indice."
            )

    db.add(
        HintUnlock(
            team_id=team_id, hint_id=hint.id, user_id=user.id, cost=hint.cost, created_at=now
        )
    )
    db.flush()
    publish(
        db,
        "team_update",
        {"reason": "hint", "user": user.username, "challenge": challenge.name},
        teams=[team_id],
        admin=False,
    )
    _publish_unlocks(db, team_id, _unlock_summary(db, team_progress(db, event, team_id, now)))
    return {"id": hint.id, "cost": hint.cost, "text_html": hint.text_html}


# --------------------------------------------------------------------------- fichiers


@router.get("/files/{file_id}")
def download_file(
    file_id: str, user: CurrentUser, db: DbSession, event: Event, now: Now, settings: AppSettings
) -> FileResponse:
    record = db.get(ChallengeFile, file_id)
    challenge = db.get(Challenge, record.challenge_id) if record else None
    # 404 dans tous les cas d'accès refusé, pour ne pas confirmer l'existence du fichier.
    allowed = record is not None and challenge is not None and challenge.active
    if allowed and not user.is_admin:
        if user.team_id is None or phase(event, now) == Phase.NOT_STARTED:
            allowed = False
        else:
            progress = team_progress(db, event, user.team_id, now)
            allowed = challenge is not None and challenge.id in progress.challenges
    if not allowed or record is None:
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
