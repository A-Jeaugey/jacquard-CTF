"""Routes publiques : informations sur l'événement, classement, annonces."""

from fastapi import APIRouter
from sqlalchemy import select

from jacquard.api.deps import DbSession, Event, Now, OptionalUser
from jacquard.api.routing import CommittingRoute
from jacquard.models import Announcement, Challenge
from jacquard.services import compute_snapshot, is_frozen, phase, public_cutoff

router = APIRouter(prefix="/api", tags=["public"], route_class=CommittingRoute)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/event")
def event_info(event: Event, now: Now) -> dict[str, object]:
    return {
        "id": event.id,
        "name": event.name,
        "tagline": event.tagline,
        "timezone": event.timezone,
        "schedule": {
            "start": event.schedule.start.isoformat(),
            "end": event.schedule.end.isoformat(),
            "freeze": event.schedule.freeze.isoformat() if event.schedule.freeze else None,
        },
        "phase": phase(event, now),
        "frozen": is_frozen(event, now),
        "server_time": now.isoformat(),
        "participation": event.participation.model_dump(),
        "flag_format": event.flag_format,
        "difficulties": event.difficulties,
        "categories": [c.model_dump() for c in event.categories],
        "board": event.board.model_dump(),
    }


@router.get("/scoreboard")
def scoreboard(db: DbSession, event: Event, now: Now, user: OptionalUser) -> dict[str, object]:
    cutoff = public_cutoff(event, now, user)
    snapshot = compute_snapshot(db, event, cutoff)
    # Défis dont l'existence est publique : ouverts d'emblée ou montrés verrouillés. Les défis
    # cachés tant qu'ils sont verrouillés ne sont pas comptés (ils restent un secret). Rangés
    # par quartier (ordre de l'événement) puis par ordre du pack, ils donnent à chaque équipe
    # la même silhouette de ville : une fenêtre par défi, toujours à la même place.
    order = {c.id: i for i, c in enumerate(event.categories)}
    public = sorted(
        (
            c
            for c in db.scalars(select(Challenge).where(Challenge.active))
            if not c.unlock or c.when_locked == "teaser"
        ),
        key=lambda c: (order.get(c.category, len(order)), c.position, c.id),
    )
    window = {c.id: i for i, c in enumerate(public)}
    counts: dict[str, int] = {}
    for c in public:
        counts[c.category] = counts.get(c.category, 0) + 1
    return {
        "frozen": cutoff is not None,
        "frozen_at": cutoff.isoformat() if cutoff else None,
        "challenges": len(public),
        "districts": [{"category": k, "count": n} for k, n in counts.items()],
        "teams": [
            {
                "rank": t.rank,
                "team_id": t.team_id,
                "name": t.name,
                "score": t.score,
                "solves": t.solves,
                "lit": sorted(window[cid] for cid in t.solved if cid in window),
                "last_solve_at": t.last_solve_at.isoformat() if t.last_solve_at else None,
            }
            for t in snapshot.teams
            if not t.hidden
        ],
    }


@router.get("/announcements")
def announcements(db: DbSession) -> list[dict[str, object]]:
    rows = db.scalars(select(Announcement).order_by(Announcement.created_at.desc()))
    return [
        {
            "id": a.id,
            "title": a.title,
            "body_html": a.body_html,
            "created_at": a.created_at.isoformat(),
        }
        for a in rows
    ]
