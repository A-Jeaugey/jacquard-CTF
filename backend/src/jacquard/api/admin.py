from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from jacquard.api.deps import Admin, DbSession, Event, Now, api_error
from jacquard.markdown import render_markdown
from jacquard.models import Announcement, Challenge, Submission, Team, User
from jacquard.services import compute_snapshot

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/teams")
def list_teams(_: Admin, db: DbSession, event: Event) -> list[dict[str, object]]:
    snapshot = compute_snapshot(db, event)
    members: dict[int, list[str]] = {}
    for team_id, username in db.execute(
        select(User.team_id, User.username).where(User.team_id.is_not(None)).order_by(User.id)
    ):
        if team_id is not None:
            members.setdefault(team_id, []).append(username)
    return [
        {
            "id": t.team_id,
            "name": t.name,
            "hidden": t.hidden,
            "rank": t.rank,
            "score": t.score,
            "solves": t.solves,
            "members": members.get(t.team_id, []),
        }
        for t in snapshot.teams
    ]


class TeamPatch(BaseModel):
    hidden: bool


@router.patch("/teams/{team_id}")
def update_team(team_id: int, body: TeamPatch, _: Admin, db: DbSession) -> dict[str, object]:
    team = db.get(Team, team_id)
    if team is None:
        api_error(404, "not_found", "Équipe introuvable.")
    team.hidden = body.hidden
    return {"id": team.id, "hidden": team.hidden}


@router.get("/submissions")
def list_submissions(
    _: Admin,
    db: DbSession,
    team_id: int | None = None,
    challenge_id: str | None = None,
    correct: bool | None = None,
    before_id: int | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict[str, object]]:
    query = (
        select(Submission, Team.name, User.username, Challenge.name)
        .join(Team, Team.id == Submission.team_id)
        .join(Challenge, Challenge.id == Submission.challenge_id)
        .outerjoin(User, User.id == Submission.user_id)
        .order_by(Submission.id.desc())
        .limit(limit)
    )
    if team_id is not None:
        query = query.where(Submission.team_id == team_id)
    if challenge_id is not None:
        query = query.where(Submission.challenge_id == challenge_id)
    if correct is not None:
        query = query.where(Submission.correct == correct)
    if before_id is not None:
        query = query.where(Submission.id < before_id)
    return [
        {
            "id": s.id,
            "team_id": s.team_id,
            "team": team_name,
            "user": username,
            "challenge_id": s.challenge_id,
            "challenge": challenge_name,
            "provided": s.provided,
            "correct": s.correct,
            "ip": s.ip,
            "created_at": s.created_at.isoformat(),
        }
        for s, team_name, username, challenge_name in db.execute(query)
    ]


class AnnouncementBody(BaseModel):
    title: str = Field(min_length=1, max_length=128)
    body: str = Field(min_length=1, max_length=10_000)


@router.post("/announcements", status_code=201)
def create_announcement(
    body: AnnouncementBody, _: Admin, db: DbSession, now: Now
) -> dict[str, object]:
    announcement = Announcement(
        title=body.title, body_html=render_markdown(body.body), created_at=now
    )
    db.add(announcement)
    db.flush()
    return {"id": announcement.id}


@router.delete("/announcements/{announcement_id}", status_code=204)
def delete_announcement(announcement_id: int, _: Admin, db: DbSession) -> None:
    announcement = db.get(Announcement, announcement_id)
    if announcement is None:
        api_error(404, "not_found", "Annonce introuvable.")
    db.delete(announcement)
