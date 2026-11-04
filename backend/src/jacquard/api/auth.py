import re
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Cookie, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from jacquard.api.deps import (
    SESSION_COOKIE,
    AppSettings,
    ClientIp,
    DbSession,
    Event,
    Now,
    OptionalUser,
    api_error,
)
from jacquard.api.routing import CommittingRoute
from jacquard.api.views import me_view
from jacquard.config import Settings
from jacquard.models import AuthSession, LoginFailure, Team, User
from jacquard.security import (
    constant_time_equals,
    hash_password,
    new_invite_code,
    new_token,
    token_digest,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"], route_class=CommittingRoute)

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")


def username_key(username: str) -> str:
    return username.casefold()


class RegisterBody(BaseModel):
    username: str = Field(max_length=32)
    password: str = Field(min_length=8, max_length=128)
    email: str | None = Field(default=None, max_length=254)
    registration_code: str | None = Field(default=None, max_length=128)


class LoginBody(BaseModel):
    username: str = Field(max_length=32)
    password: str = Field(max_length=128)


def _open_session(
    db: DbSession, response: Response, user: User, settings: Settings, now: Now
) -> None:
    token = new_token()
    ttl = timedelta(hours=settings.session_ttl_hours)
    db.add(
        AuthSession(
            token_hash=token_digest(token), user_id=user.id, created_at=now, expires_at=now + ttl
        )
    )
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(ttl.total_seconds()),
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


@router.post("/register", status_code=201)
def register(
    body: RegisterBody,
    db: DbSession,
    event: Event,
    settings: AppSettings,
    now: Now,
    response: Response,
) -> dict[str, object]:
    mode = event.participation.registration
    if mode == "closed":
        api_error(403, "registration_closed", "Les inscriptions sont fermées.")
    if mode == "invite_code":
        expected = settings.registration_code
        if expected is None:
            api_error(503, "registration_misconfigured", "Code d'inscription non configuré.")
        if not body.registration_code or not constant_time_equals(
            body.registration_code.strip(), expected.get_secret_value()
        ):
            api_error(
                403,
                "bad_registration_code",
                "Code d'inscription invalide : vérifie-le auprès des organisateurs.",
            )

    username = body.username.strip()
    if not USERNAME_RE.fullmatch(username):
        api_error(
            422,
            "invalid_username",
            "Le pseudo doit faire 3 à 32 caractères : lettres, chiffres, « _ », « . » ou « - ».",
        )
    email = body.email.strip() if body.email else None
    if email and ("@" not in email or any(ch.isspace() for ch in email)):
        api_error(422, "invalid_email", "Adresse e-mail invalide.")

    # Le hachage est volontairement lent : on rend d'abord la connexion à la base au pool,
    # pour qu'une vague d'inscriptions ne bloque pas les autres requêtes.
    db.commit()
    password_hash = hash_password(body.password)
    user = User(
        username=username,
        username_key=username_key(username),
        email=email or None,
        password_hash=password_hash,
    )
    if event.participation.mode == "solo":
        user.team = Team(
            name=username, name_key=username_key(username), invite_code=new_invite_code()
        )
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        api_error(409, "username_taken", "Ce pseudo est déjà pris : choisis-en un autre.")
    _open_session(db, response, user, settings, now)
    return me_view(db, user)


@router.post("/login")
def login(
    body: LoginBody,
    db: DbSession,
    settings: AppSettings,
    now: Now,
    ip: ClientIp,
    response: Response,
) -> dict[str, object]:
    key = username_key(body.username.strip())
    since = now - timedelta(seconds=settings.login_window_seconds)
    failures_for_user = db.scalar(
        select(func.count()).where(
            LoginFailure.username_key == key, LoginFailure.created_at > since
        )
    )
    failures_for_ip = db.scalar(
        select(func.count()).where(LoginFailure.ip == ip, LoginFailure.created_at > since)
    )
    if (failures_for_user or 0) >= settings.login_max_failures or (
        failures_for_ip or 0
    ) >= settings.login_max_failures * 5:
        api_error(429, "too_many_attempts", "Trop de tentatives, réessaie dans quelques minutes.")

    user = db.scalar(select(User).where(User.username_key == key))
    stored_hash = user.password_hash if user else None
    db.commit()  # connexion rendue au pool pendant la vérification (lente) du mot de passe
    if not verify_password(stored_hash, body.password) or user is None:
        db.add(LoginFailure(username_key=key[:32], ip=ip, created_at=now))
        db.commit()
        api_error(401, "invalid_credentials", "Pseudo ou mot de passe incorrect.")

    db.execute(delete(LoginFailure).where(LoginFailure.username_key == key))
    db.execute(
        delete(AuthSession).where(AuthSession.user_id == user.id, AuthSession.expires_at <= now)
    )
    _open_session(db, response, user, settings, now)
    return me_view(db, user)


@router.post("/logout", status_code=204)
def logout(
    db: DbSession,
    response: Response,
    settings: AppSettings,
    jq_session: Annotated[str | None, Cookie()] = None,
) -> None:
    if jq_session:
        db.execute(delete(AuthSession).where(AuthSession.token_hash == token_digest(jq_session)))
    response.delete_cookie(SESSION_COOKIE, path="/", secure=settings.cookie_secure, httponly=True)


@router.get("/me")
def me(user: OptionalUser, db: DbSession) -> dict[str, object] | None:
    return me_view(db, user) if user else None
