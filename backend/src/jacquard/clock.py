"""Source unique de l'heure courante, remplaçable dans les tests."""

from datetime import UTC, datetime


def utcnow() -> datetime:
    return datetime.now(UTC)


def get_now() -> datetime:
    """Dépendance FastAPI ; les tests la surchargent pour simuler l'horaire de l'événement."""
    return utcnow()
