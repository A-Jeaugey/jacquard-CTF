"""Répétitions : décaler l'horaire d'un pack sans modifier ses fichiers."""

import dataclasses
import hashlib
from datetime import datetime

from jacquard.packs.loader import Pack
from jacquard.packs.schema import Schedule


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
