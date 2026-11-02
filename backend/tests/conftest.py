import os
import shutil
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml

os.environ.setdefault(
    "JACQUARD_DATABASE_URL",
    os.environ.get(
        "JACQUARD_TEST_DATABASE_URL", "postgresql+psycopg://postgres@localhost:5432/jacquard_test"
    ),
)
os.environ["JACQUARD_SECRET_KEY"] = "test-secret-key-which-is-long-enough-0123456789"
os.environ["JACQUARD_COOKIE_SECURE"] = "false"
os.environ.pop("JACQUARD_REGISTRATION_CODE", None)

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from jacquard.clock import get_now
from jacquard.config import get_settings
from jacquard.db import Base, get_engine, get_sessionmaker
from jacquard.main import create_app
from jacquard.models import User
from jacquard.packs.loader import load_pack
from jacquard.packs.sync import sync_pack
from jacquard.security import hash_password

DEMO_PACK = Path(__file__).resolve().parents[2] / "examples" / "demo-pack"


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2027, 6, 1, 12, 0, tzinfo=UTC)

    def set(self, moment: datetime) -> None:
        self.now = moment

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture(scope="session", autouse=True)
def _schema() -> Iterator[None]:
    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def _clean_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with get_engine().begin() as connection:
        connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    monkeypatch.setattr(get_settings(), "data_dir", tmp_path / "data")
    yield


@pytest.fixture
def db() -> Iterator[Session]:
    with get_sessionmaker()() as session:
        yield session


@pytest.fixture
def clock() -> Clock:
    return Clock()


def _deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


@pytest.fixture
def make_pack(tmp_path: Path):  # type: ignore[no-untyped-def]
    """Copie le pack de démo et surcharge son event.yml."""

    def factory(**overrides: Any) -> Path:
        target = tmp_path / f"pack-{len(list(tmp_path.glob('pack-*')))}"
        shutil.copytree(DEMO_PACK, target)
        event_path = target / "event.yml"
        event = yaml.safe_load(event_path.read_text(encoding="utf-8"))
        event_path.write_text(yaml.safe_dump(_deep_merge(event, overrides)), encoding="utf-8")
        return target

    return factory


@pytest.fixture
def sync(db: Session):  # type: ignore[no-untyped-def]
    def run(path: Path = DEMO_PACK) -> None:
        settings = get_settings()
        sync_pack(
            db,
            load_pack(path),
            secret=settings.secret_key.get_secret_value(),
            files_dir=settings.files_dir,
            now=datetime.now(UTC),
        )

    return run


class ApiClient:
    """Client de test qui recopie automatiquement le jeton CSRF."""

    def __init__(self, client: TestClient) -> None:
        self.client = client
        self.client.get("/api/health")

    def _headers(self) -> dict[str, str]:
        token = self.client.cookies.get("jq_csrf")
        return {"X-CSRF-Token": token} if token else {}

    def get(self, url: str, **kwargs: Any) -> Any:
        return self.client.get(url, **kwargs)

    def post(self, url: str, json: Any = None, **kwargs: Any) -> Any:
        return self.client.post(url, json=json, headers=self._headers(), **kwargs)

    def patch(self, url: str, json: Any = None) -> Any:
        return self.client.patch(url, json=json, headers=self._headers())

    def delete(self, url: str) -> Any:
        return self.client.delete(url, headers=self._headers())

    def register(self, username: str, password: str = "motdepasse-solide", **extra: Any) -> Any:
        response = self.post(
            "/api/auth/register", {"username": username, "password": password, **extra}
        )
        assert response.status_code == 201, response.text
        return response.json()

    def create_team(self, name: str) -> dict[str, Any]:
        response = self.post("/api/teams", {"name": name})
        assert response.status_code == 201, response.text
        return response.json()  # type: ignore[no-any-return]

    def submit(self, challenge_id: str, flag: str) -> Any:
        return self.post(f"/api/challenges/{challenge_id}/submit", {"flag": flag})


@pytest.fixture
def app(clock: Clock):  # type: ignore[no-untyped-def]
    application = create_app()
    application.dependency_overrides[get_now] = clock
    return application


@pytest.fixture
def new_client(app):  # type: ignore[no-untyped-def]
    clients: list[TestClient] = []

    def factory() -> ApiClient:
        client = TestClient(app)
        clients.append(client)
        return ApiClient(client)

    yield factory
    for client in clients:
        client.close()


@pytest.fixture
def player(new_client, sync):  # type: ignore[no-untyped-def]
    """Joueur inscrit, dans une équipe, pack de démo importé."""
    sync()
    api = new_client()
    api.register("alice")
    api.create_team("Les Testeurs")
    return api


@pytest.fixture
def admin(new_client, db: Session):  # type: ignore[no-untyped-def]
    db.add(
        User(
            username="orga",
            username_key="orga",
            password_hash=hash_password("admin-password-123"),
            role="admin",
        )
    )
    db.commit()
    api = new_client()
    response = api.post("/api/auth/login", {"username": "orga", "password": "admin-password-123"})
    assert response.status_code == 200, response.text
    return api
