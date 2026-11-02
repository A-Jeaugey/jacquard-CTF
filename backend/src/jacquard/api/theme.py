"""Thème du pack, grand écran et fil d'actualité public."""

from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import FileResponse
from sqlalchemy import func, select

from jacquard.api.deps import AppSettings, DbSession, Event, Now, api_error
from jacquard.api.routing import CommittingRoute
from jacquard.models import Announcement, Challenge, EventRow, Solve, Team, ThemeAsset
from jacquard.services import is_frozen, public_challenge_name

router = APIRouter(prefix="/api", tags=["theme"], route_class=CommittingRoute)

ASSET_PREFIX = "/api/theme/assets/"


@router.get("/theme")
def theme(db: DbSession) -> dict[str, object]:
    row = db.get(EventRow, 1)
    config = (row.theme if row else None) or {}
    versions = dict(db.execute(select(ThemeAsset.path, ThemeAsset.sha256)).all())

    def url(path: str | None) -> str | None:
        # La version dans l'URL évite qu'un navigateur garde un ancien fichier en cache.
        return f"{ASSET_PREFIX}{path}?v={versions[path][:12]}" if path in versions else None

    return {
        "tokens": config.get("tokens", {}),
        "strings": config.get("strings", {}),
        "logo_url": url(config.get("logo")),
        "css_url": url(config.get("css")),
        "layouts": {
            layout_id: {
                "type": layout["type"],
                "background_url": url(layout["background"]),
                "zones": layout["zones"],
            }
            for layout_id, layout in config.get("layouts", {}).items()
        },
    }


@router.get("/theme/assets/{path:path}")
def theme_asset(path: str, db: DbSession, settings: AppSettings) -> FileResponse:
    asset = db.get(ThemeAsset, path)
    file = settings.files_dir / asset.sha256 if asset else None
    if asset is None or file is None or not file.is_file():
        api_error(404, "not_found", "Fichier introuvable.")
    return FileResponse(file, media_type=asset.content_type)


def _cutoff(event: Event, now: Now) -> datetime | None:
    return event.schedule.freeze if is_frozen(event, now) else None


@router.get("/screens/{screen_id}")
def screen(screen_id: str, db: DbSession, event: Event, now: Now) -> dict[str, object]:
    """Progression globale par catégorie, sans rien révéler des défis eux-mêmes."""
    config = next((s for s in event.screens if s.id == screen_id), None)
    if config is None:
        api_error(404, "not_found", "Écran introuvable.")
    cutoff = _cutoff(event, now)
    visible_teams = select(Team.id).where(Team.hidden.is_(False))
    solves = select(Challenge.category, func.count(Solve.id)).join(
        Challenge, Challenge.id == Solve.challenge_id
    )
    solves = solves.where(Challenge.active, Solve.team_id.in_(visible_teams))
    if cutoff is not None:
        solves = solves.where(Solve.created_at < cutoff)
    solved_by_category = dict(db.execute(solves.group_by(Challenge.category)).all())
    totals = dict(
        db.execute(
            select(Challenge.category, func.count())
            .where(Challenge.active)
            .group_by(Challenge.category)
        ).all()
    )
    active_query = select(func.count(func.distinct(Solve.team_id))).where(
        Solve.team_id.in_(visible_teams)
    )
    if cutoff is not None:
        active_query = active_query.where(Solve.created_at < cutoff)
    active_teams = db.scalar(active_query) or 0
    return {
        "id": config.id,
        "title": config.title or event.name,
        "layout": config.layout,
        "frozen": cutoff is not None,
        "active_teams": active_teams,
        "categories": [
            {
                "id": category.id,
                "name": category.name,
                "color": category.color,
                # Part moyenne des défis de la catégorie résolus par les équipes actives.
                "progress": (
                    min(
                        1.0,
                        solved_by_category.get(category.id, 0)
                        / (active_teams * totals[category.id]),
                    )
                    if active_teams and totals.get(category.id)
                    else 0.0
                ),
            }
            for category in event.categories
        ],
    }


@router.get("/feed")
def feed(db: DbSession, event: Event, now: Now) -> list[dict[str, object]]:
    """Derniers premiers sangs et annonces, pour le grand écran."""
    cutoff = _cutoff(event, now)
    first = (
        select(Solve.challenge_id, func.min(Solve.created_at).label("at"))
        .join(Team, Team.id == Solve.team_id)
        .where(Team.hidden.is_(False))
        .group_by(Solve.challenge_id)
        .subquery()
    )
    query = (
        select(Solve.created_at, Team.name, Challenge)
        .join(
            first, (first.c.challenge_id == Solve.challenge_id) & (first.c.at == Solve.created_at)
        )
        .join(Team, Team.id == Solve.team_id)
        .join(Challenge, Challenge.id == Solve.challenge_id)
        .where(Challenge.active, Team.hidden.is_(False))
    )
    if cutoff is not None:
        query = query.where(Solve.created_at < cutoff)
    items: list[dict[str, object]] = [
        {
            "kind": "first_blood",
            "at": at.isoformat(),
            "team": team,
            "challenge": public_challenge_name(challenge),
        }
        for at, team, challenge in db.execute(query.order_by(Solve.created_at.desc()).limit(20))
    ]
    items += [
        {"kind": "announcement", "at": a.created_at.isoformat(), "title": a.title}
        for a in db.scalars(select(Announcement).order_by(Announcement.created_at.desc()).limit(10))
    ]
    return sorted(items, key=lambda i: str(i["at"]), reverse=True)[:20]
