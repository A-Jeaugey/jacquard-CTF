"""Sérialisation des objets renvoyés par l'API.

Centraliser ces fonctions permet de vérifier en un seul endroit ce qui sort de la
plateforme (jamais de condensat de flag, de mot de passe ou de contenu verrouillé).
"""

from sqlalchemy.orm import Session

from jacquard.models import Team, User


def user_view(user: User) -> dict[str, object]:
    return {"id": user.id, "username": user.username, "role": user.role}


def me_view(db: Session, user: User) -> dict[str, object]:
    team = db.get(Team, user.team_id) if user.team_id else None
    return {
        "user": user_view(user),
        "team": {"id": team.id, "name": team.name} if team else None,
    }
