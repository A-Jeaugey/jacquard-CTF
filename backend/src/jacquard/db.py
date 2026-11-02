from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from jacquard.config import get_settings


class Base(DeclarativeBase):
    pass


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
    )


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


async def get_db() -> AsyncIterator[Session]:
    """Dépendance FastAPI : une session par requête, validée à la fin (annulée en cas d'erreur).

    Dépendance **asynchrone** : son nettoyage (commit, fermeture) s'exécute dans la boucle
    d'événements au lieu d'attendre un fil d'exécution libre. Avec une dépendance
    synchrone, une vague de plus de 40 requêtes simultanées pouvait bloquer : les fils
    attendaient des connexions, et les connexions attendaient un fil pour être rendues
    (constaté au test de charge). Le commit final est bref : il ne bloque la boucle que
    quelques millisecondes, et seulement pour les requêtes qui ont écrit."""
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
