from fastapi import APIRouter
from sqlalchemy import select

from jacquard.api.deps import DbSession, Event, Now, OptionalUser
from jacquard.models import StoryEntry
from jacquard.services import Phase, phase, team_progress

router = APIRouter(prefix="/api", tags=["story"])


@router.get("/story")
def story(user: OptionalUser, db: DbSession, event: Event, now: Now) -> dict[str, object]:
    """Chapitres visibles : les chapitres publics pour tous, et ceux que l'équipe a
    débloqués. Le nombre de chapitres restants est indiqué, sans leur titre."""
    entries = list(
        db.scalars(
            select(StoryEntry).where(StoryEntry.active).order_by(StoryEntry.position, StoryEntry.id)
        )
    )
    if user is not None and user.is_admin:
        unlocked = {e.id for e in entries}
    elif user is not None and user.team_id is not None and phase(event, now) != Phase.NOT_STARTED:
        unlocked = team_progress(db, event, user.team_id, now).story
    else:
        unlocked = set()

    visible = [e for e in entries if e.public or e.id in unlocked]
    return {
        "entries": [
            {"id": e.id, "title": e.title, "body_html": e.body_html, "public": e.public}
            for e in visible
        ],
        "locked": len(entries) - len(visible),
    }
