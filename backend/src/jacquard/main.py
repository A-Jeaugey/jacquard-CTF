import secrets
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from jacquard import __version__
from jacquard.api import admin, auth, challenges, live, public, story, teams
from jacquard.api.deps import CSRF_COOKIE, CSRF_HEADER
from jacquard.config import get_settings
from jacquard.realtime import broker
from jacquard.security import constant_time_equals

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Cache-Control": "no-store",
}


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if settings.realtime:
        broker.start(settings.database_url)
    yield
    await broker.stop()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Jacquard",
        lifespan=lifespan,
        version=__version__,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )

    @app.middleware("http")
    async def csrf_and_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Protection CSRF par double soumission : le cookie `jq_csrf`, lisible par le
        frontend, doit être recopié dans l'en-tête `X-CSRF-Token` des requêtes qui
        modifient l'état. Un site tiers ne peut pas lire ce cookie."""
        cookie = request.cookies.get(CSRF_COOKIE)
        if request.method not in SAFE_METHODS and request.url.path.startswith("/api/"):
            header = request.headers.get(CSRF_HEADER)
            if not cookie or not header or not constant_time_equals(cookie, header):
                response: Response = JSONResponse(
                    status_code=403,
                    content={
                        "detail": {"code": "csrf", "message": "Jeton CSRF manquant ou invalide."}
                    },
                )
            else:
                response = await call_next(request)
        else:
            response = await call_next(request)

        if not cookie:
            response.set_cookie(
                CSRF_COOKIE,
                secrets.token_urlsafe(32),
                httponly=False,
                secure=get_settings().cookie_secure,
                samesite="strict",
                path="/",
            )
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        return response

    for module in (public, auth, teams, challenges, story, live, admin):
        app.include_router(module.router)
    return app


app = create_app()
