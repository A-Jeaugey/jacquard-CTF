"""Répétitions : décaler l'horaire d'un pack, ou viser d'autres serveurs de défis, sans
modifier ses fichiers."""

import dataclasses
import hashlib
import re
from datetime import datetime

from jacquard.packs.loader import Pack
from jacquard.packs.schema import HOST_PATTERN, Schedule


def shift_schedule(pack: Pack, start: datetime) -> Pack:
    """Copie du pack dont l'événement commence à `start`, en gardant sa durée et le délai
    avant le gel. Les règles `time.elapsed_minutes` suivent ; les dates absolues
    (`time.after`, `time.before`) ne sont pas décalées."""
    schedule = pack.event.schedule
    delta = start - schedule.start
    shifted = Schedule(
        start=start,
        end=schedule.end + delta,
        freeze=schedule.freeze + delta if schedule.freeze else None,
    )
    event = pack.event.model_copy(update={"schedule": shifted})
    digest = hashlib.sha256(f"{pack.digest}:{start.isoformat()}".encode()).hexdigest()
    return dataclasses.replace(pack, event=event, digest=digest)


def override_challenge_host(pack: Pack, host: str) -> Pack:
    """Copie du pack dont les `{challenge_host}` désignent `host` (machine de répétition,
    adresse de secours le jour J…). Lève ValueError si le nom d'hôte est invalide."""
    if not re.fullmatch(HOST_PATTERN, host):
        raise ValueError(f"nom d'hôte invalide : {host!r}")
    event = pack.event.model_copy(update={"challenge_host": host})
    digest = hashlib.sha256(f"{pack.digest}:host={host}".encode()).hexdigest()
    return dataclasses.replace(pack, event=event, digest=digest)
