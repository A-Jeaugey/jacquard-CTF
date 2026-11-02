import re

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import exists, func, select
from sqlalchemy.exc import IntegrityError

from jacquard.api.deps import CurrentUser, DbSession, Event, api_error
from jacquard.api.routing import CommittingRoute
from jacquard.models import Challenge, Solve, Team, User
from jacquard.security import new_invite_code
from jacquard.services import compute_snapshot

router = APIRouter(prefix="/api/teams", tags=["teams"], route_class=CommittingRoute)

_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def normalize_team_name(raw: str) -> tuple[str, str]:
    name = " ".join(raw.split())
    if not 2 <= len(name) <= 64 or _CONTROL.search(name):
        api_error(422, "invalid_team_name", "Le nom d'équipe doit faire entre 2 et 64 caractères.")
    return name, name.casefold()


class CreateTeamBody(BaseModel):
    name: str = Field(max_length=128)


class JoinTeamBody(BaseModel):
    invite_code: str = Field(max_length=64)


def _require_team_mode(event: Event) -> None:
    if event.participation.mode != "teams":
        api_error(403, "solo_mode", "Cet événement se joue en solo.")


def _require_no_team(db: DbSession, user: User) -> None:
    # Verrou sur l'utilisateur : deux requêtes simultanées ne peuvent pas lui donner deux équipes.
    db.refresh(user, with_for_update=True)
    if user.team_id is not None:
        api_error(409, "already_in_team", "Tu fais déjà partie d'une équipe.")


@router.post("", status_code=201)
def create_team(
    body: CreateTeamBody, user: CurrentUser, db: DbSession, event: Event
) -> dict[str, object]:
    _require_team_mode(event)
    _require_no_team(db, user)
    name, key = normalize_team_name(body.name)
    team = Team(name=name, name_key=key, invite_code=new_invite_code())
    db.add(team)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        api_error(409, "team_name_taken", "Ce nom d'équipe est déjà pris.")
    user.team_id = team.id
    db.flush()
    return team_detail(db, event, team)


@router.post("/join")
def join_team(
    body: JoinTeamBody, user: CurrentUser, db: DbSession, event: Event
) -> dict[str, object]:
    _require_team_mode(event)
    _require_no_team(db, user)
    code = body.invite_code.strip().upper()
    # Verrou sur l'équipe : deux arrivées simultanées ne peuvent pas dépasser la limite.
    team = db.scalar(select(Team).where(Team.invite_code == code).with_for_update())
    if team is None:
        api_error(404, "invalid_invite_code", "Code d'invitation invalide.")
    members = db.scalar(select(func.count()).where(User.team_id == team.id)) or 0
    if members >= event.participation.team_size.max:
        api_error(409, "team_full", "Cette équipe est complète.")
    user.team_id = team.id
    db.flush()
    return team_detail(db, event, team)


@router.post("/leave", status_code=204)
def leave_team(user: CurrentUser, db: DbSession, event: Event) -> None:
    _require_team_mode(event)
    if user.team_id is None:
        api_error(409, "no_team", "Tu ne fais partie d'aucune équipe.")
    team = db.scalar(select(Team).where(Team.id == user.team_id).with_for_update())
    assert team is not None
    if db.scalar(select(exists().where(Solve.team_id == team.id))):
        api_error(
            409,
            "team_has_solves",
            "Impossible de quitter une équipe qui a déjà marqué des points.",
        )
    user.team_id = None
    db.flush()
    if not db.scalar(select(exists().where(User.team_id == team.id))):
        db.delete(team)


@router.get("/me")
def my_team(user: CurrentUser, db: DbSession, event: Event) -> dict[str, object] | None:
    team = db.get(Team, user.team_id) if user.team_id else None
    return team_detail(db, event, team) if team else None


def team_detail(db: DbSession, event: Event, team: Team) -> dict[str, object]:
    """Vue complète de l'équipe, pour ses membres : score réel, même pendant le gel."""
    snapshot = compute_snapshot(db, event)
    score = snapshot.team(team.id)
    members = db.scalars(select(User).where(User.team_id == team.id).order_by(User.id))
    solves = db.execute(
        select(Solve.challenge_id, Challenge.name, Solve.created_at, User.username)
        .join(Challenge, Challenge.id == Solve.challenge_id)
        .outerjoin(User, User.id == Solve.user_id)
        .where(Solve.team_id == team.id, Challenge.active)
        .order_by(Solve.created_at)
    )
    solved = db.scalars(
        select(Challenge)
        .join(Solve, Solve.challenge_id == Challenge.id)
        .where(Solve.team_id == team.id, Challenge.active)
    )
    owned = {item for challenge in solved for item in challenge.granted_items}
    return {
        "id": team.id,
        "name": team.name,
        "invite_code": team.invite_code if event.participation.mode == "teams" else None,
        "penalty": score.penalty if score else 0,
        "items": [
            {"id": i.id, "name": i.name, "description": i.description}
            for i in event.items
            if i.id in owned
        ],
        "max_size": event.participation.team_size.max,
        "members": [{"id": m.id, "username": m.username} for m in members],
        "score": score.score if score else 0,
        "rank": score.rank if score else None,
        "solves": [
            {
                "challenge_id": cid,
                "challenge_name": name,
                "solved_at": at.isoformat(),
                "solved_by": username,
                "points": score.solved.get(cid, 0) if score else 0,
            }
            for cid, name, at, username in solves
        ],
    }
