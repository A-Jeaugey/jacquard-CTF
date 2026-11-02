"""Dépendances FastAPI communes : utilisateur courant, événement, erreurs."""

from datetime import datetime
from typing import Annotated, NoReturn

from fastapi import Cookie, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from jacquard.clock import get_now
from jacquard.config import Settings, get_settings
from jacquard.db import get_db
from jacquard.models import AuthSession, User
from jacquard.packs.schema import EventConfig
from jacquard.security import token_digest
from jacquard.services import load_event

SESSION_COOKIE = "jq_session"
CSRF_COOKIE = "jq_csrf"
CSRF_HEADER = "X-CSRF-Token"


def api_error(status: int, code: str, message: str, **extra: object) -> NoReturn:
    raise HTTPException(status_code=status, detail={"code": code, "message": message, **extra})


DbSession = Annotated[Session, Depends(get_db)]
Now = Annotated[datetime, Depends(get_now)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def get_event(db: DbSession) -> EventConfig:
    event = load_event(db)
    if event is None:
        api_error(503, "event_not_configured", "Aucun événement n'a encore été importé.")
    return event


Event = Annotated[EventConfig, Depends(get_event)]


def get_optional_user(
    db: DbSession,
    now: Now,
    jq_session: Annotated[str | None, Cookie()] = None,
) -> User | None:
    if not jq_session:
        return None
    auth = db.get(AuthSession, token_digest(jq_session))
    if auth is None or auth.expires_at <= now:
        return None
    return db.get(User, auth.user_id)


OptionalUser = Annotated[User | None, Depends(get_optional_user)]


def get_user(user: OptionalUser) -> User:
    if user is None:
        api_error(401, "not_authenticated", "Connexion requise.")
    return user


CurrentUser = Annotated[User, Depends(get_user)]


def get_admin(user: CurrentUser) -> User:
    if not user.is_admin:
        api_error(403, "forbidden", "Accès réservé à l'organisation.")
    return user


Admin = Annotated[User, Depends(get_admin)]


def client_ip(request: Request) -> str:
    # Derrière le proxy, uvicorn réécrit request.client à partir de X-Forwarded-For
    # (option --forwarded-allow-ips), on peut donc s'y fier.
    return request.client.host if request.client else "unknown"


ClientIp = Annotated[str, Depends(client_ip)]
