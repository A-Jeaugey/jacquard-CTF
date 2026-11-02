from collections import Counter, defaultdict
from datetime import datetime, timedelta
from statistics import median

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from jacquard.api.deps import Admin, DbSession, Event, Now, api_error
from jacquard.markdown import render_markdown
from jacquard.models import (
    Announcement,
    Challenge,
    Hint,
    HintUnlock,
    Solve,
    Submission,
    Team,
    User,
)
from jacquard.realtime import publish
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
    publish(db, "announcement", {"id": announcement.id, "title": announcement.title}, public=True)
    return {"id": announcement.id}


@router.delete("/announcements/{announcement_id}", status_code=204)
def delete_announcement(announcement_id: int, _: Admin, db: DbSession) -> None:
    announcement = db.get(Announcement, announcement_id)
    if announcement is None:
        api_error(404, "not_found", "Annonce introuvable.")
    db.delete(announcement)


# --------------------------------------------------------------------------- statistiques


@router.get("/stats")
def stats(_: Admin, db: DbSession, event: Event) -> dict[str, object]:
    """Statistiques par défi et signaux à vérifier, pour l'orga (pendant et après l'événement).

    Les signaux ne sont que des pistes : sans flags par équipe, aucune preuve de partage."""


    hidden = set(db.scalars(select(Team.id).where(Team.hidden)))
    names = dict(db.execute(select(Team.id, Team.name)).all())
    submissions = [
        s
        for s in db.scalars(select(Submission).order_by(Submission.created_at))
        if s.team_id not in hidden
    ]
    solves = [
        s for s in db.scalars(select(Solve).order_by(Solve.created_at)) if s.team_id not in hidden
    ]
    hint_owner = dict(db.execute(select(Hint.id, Hint.challenge_id)).all())
    hints = Counter(
        hint_owner.get(h.hint_id) for h in db.scalars(select(HintUnlock)) if h.team_id not in hidden
    )
    start = event.schedule.start

    def minutes(moment: datetime) -> float:
        return round((moment - start).total_seconds() / 60, 1)

    by_challenge: dict[str, list[Submission]] = defaultdict(list)
    for submission in submissions:
        by_challenge[submission.challenge_id].append(submission)
    solve_times: dict[str, list[float]] = defaultdict(list)
    for solve in solves:
        solve_times[solve.challenge_id].append(minutes(solve.created_at))

    challenges = []
    for challenge in db.scalars(
        select(Challenge).where(Challenge.active).order_by(Challenge.category, Challenge.position)
    ):
        attempts = by_challenge.get(challenge.id, [])
        wrong = Counter(s.provided for s in attempts if not s.correct)
        times = solve_times.get(challenge.id, [])
        challenges.append(
            {
                "id": challenge.id,
                "name": challenge.name,
                "category": challenge.category,
                "solves": len(times),
                "attempts": len(attempts),
                "wrong": sum(wrong.values()),
                "hints": hints.get(challenge.id, 0),
                "first_solve_minutes": times[0] if times else None,
                "median_solve_minutes": median(times) if times else None,
                "top_wrong": [{"value": v, "count": c} for v, c in wrong.most_common(3)],
            }
        )

    signals: list[dict[str, object]] = []
    # Même adresse IP utilisée par plusieurs équipes (peu fiable derrière un NAT commun).
    teams_by_ip: dict[str, set[int]] = defaultdict(set)
    for submission in submissions:
        teams_by_ip[submission.ip].add(submission.team_id)
    for ip, teams in sorted(teams_by_ip.items()):
        if len(teams) >= 2:
            signals.append(
                {"kind": "shared_ip", "ip": ip, "teams": sorted(names[t] for t in teams)}
            )
    # Rafale : au moins 4 défis résolus en 5 minutes par une même équipe.
    solves_by_team: dict[int, list[Solve]] = defaultdict(list)
    for solve in solves:
        solves_by_team[solve.team_id].append(solve)
    for team_id, team_solves in solves_by_team.items():
        for i in range(len(team_solves) - 3):
            if team_solves[i + 3].created_at - team_solves[i].created_at <= timedelta(minutes=5):
                signals.append(
                    {
                        "kind": "burst",
                        "team": names[team_id],
                        "at_minutes": minutes(team_solves[i].created_at),
                    }
                )
                break
    # Même mauvaise réponse, assez longue pour ne pas être une coïncidence, chez 3 équipes ou plus.
    teams_by_wrong: dict[tuple[str, str], set[int]] = defaultdict(set)
    for submission in submissions:
        if not submission.correct and len(submission.provided) >= 12:
            teams_by_wrong[(submission.challenge_id, submission.provided)].add(submission.team_id)
    for (challenge_id, value), teams in sorted(teams_by_wrong.items()):
        if len(teams) >= 3:
            signals.append(
                {
                    "kind": "same_wrong_answer",
                    "challenge": challenge_id,
                    "value": value,
                    "teams": sorted(names[t] for t in teams),
                }
            )
    return {"challenges": challenges, "signals": signals}
