"""Classe de route commune : valide la transaction dans le fil du gestionnaire.

Pour une route synchrone, FastAPI exécute le gestionnaire dans un fil, puis sérialise la
réponse dans un autre fil, et seulement ensuite nettoie les dépendances (commit de la
session). Pendant ces attentes, la connexion à la base restait prise. Lors d'une vague de
requêtes, tous les fils pouvaient attendre une connexion tenue par des requêtes qui
attendaient elles-mêmes un fil : blocage jusqu'au délai d'expiration du pool (constaté au
test de charge, avec py-spy). Ici, la transaction est validée dès que le gestionnaire
rend sa valeur, dans le même fil : plus aucune connexion n'est tenue pendant l'attente.
"""

import functools
import inspect
from collections.abc import Callable
from typing import Any

from fastapi.routing import APIRoute
from sqlalchemy.orm import Session


def _commit_after(endpoint: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(endpoint)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        result = endpoint(*args, **kwargs)
        for value in kwargs.values():
            if isinstance(value, Session):
                value.commit()
        return result

    return wrapper


class CommittingRoute(APIRoute):
    def __init__(self, path: str, endpoint: Callable[..., Any], **kwargs: Any) -> None:
        if not inspect.iscoroutinefunction(endpoint):
            endpoint = _commit_after(endpoint)
        super().__init__(path, endpoint, **kwargs)
