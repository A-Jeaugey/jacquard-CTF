"""Schéma des fichiers d'un pack d'événement.

Les modèles refusent les champs inconnus : une faute de frappe dans un YAML (ou un champ
pas encore pris en charge par cette version) est signalée à la validation plutôt
qu'ignorée silencieusement.
"""

import re
from datetime import datetime
from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ID_PATTERN = r"^[a-z0-9][a-z0-9-]{0,63}$"
Identifier = Annotated[str, Field(pattern=ID_PATTERN)]
HexColor = Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# --------------------------------------------------------------------------- scoring


class StaticScoring(StrictModel):
    type: Literal["static"]
    value: int = Field(ge=0)


class DynamicScoring(StrictModel):
    """La valeur décroît de `initial` à `minimum`, atteint quand `decay` équipes ont résolu
    le défi après la première."""

    type: Literal["dynamic"]
    initial: int = Field(ge=0)
    minimum: int = Field(ge=0)
    decay: int = Field(ge=1)

    @model_validator(mode="after")
    def _check_bounds(self) -> "DynamicScoring":
        if self.minimum > self.initial:
            raise ValueError("`minimum` doit être inférieur ou égal à `initial`")
        return self


Scoring = Annotated[StaticScoring | DynamicScoring, Field(discriminator="type")]


# --------------------------------------------------------------------------- event.yml


class Schedule(StrictModel):
    start: datetime
    end: datetime
    freeze: datetime | None = None


class TeamSize(StrictModel):
    min: int = Field(default=1, ge=1)
    max: int = Field(default=4, ge=1, le=50)

    @model_validator(mode="after")
    def _check_bounds(self) -> "TeamSize":
        if self.min > self.max:
            raise ValueError("`min` doit être inférieur ou égal à `max`")
        return self


class Participation(StrictModel):
    mode: Literal["teams", "solo"] = "teams"
    team_size: TeamSize = TeamSize()
    registration: Literal["open", "invite_code", "closed"] = "open"


class Category(StrictModel):
    id: Identifier
    name: str = Field(min_length=1, max_length=64)
    description: str | None = None
    color: HexColor | None = None


class RateLimit(StrictModel):
    max: int = Field(default=10, ge=1)
    per_seconds: int = Field(default=60, ge=1)


class Submissions(StrictModel):
    rate_limit: RateLimit = RateLimit()


class EventScoring(StrictModel):
    default: Scoring = StaticScoring(type="static", value=100)
    first_blood: list[Annotated[int, Field(ge=0)]] = Field(default_factory=list, max_length=10)


class Board(StrictModel):
    layout: Literal["grid"] = "grid"


class EventConfig(StrictModel):
    id: Identifier
    name: str = Field(min_length=1, max_length=128)
    tagline: str | None = Field(default=None, max_length=256)
    timezone: str = "Europe/Paris"
    schedule: Schedule
    participation: Participation = Participation()
    flag_format: str | None = Field(default=None, max_length=128)
    difficulties: list[str] = Field(default_factory=list)
    categories: list[Category] = Field(min_length=1)
    scoring: EventScoring = EventScoring()
    submissions: Submissions = Submissions()
    board: Board = Board()

    @field_validator("timezone")
    @classmethod
    def _check_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"fuseau horaire inconnu : {value}") from exc
        return value

    @model_validator(mode="after")
    def _localize_and_check(self) -> "EventConfig":
        tz = ZoneInfo(self.timezone)

        def localize[T: (datetime, datetime | None)](moment: T) -> T:
            if moment is None or moment.tzinfo is not None:
                return moment
            return moment.replace(tzinfo=tz)

        schedule = Schedule(
            start=localize(self.schedule.start),
            end=localize(self.schedule.end),
            freeze=localize(self.schedule.freeze),
        )
        if schedule.end <= schedule.start:
            raise ValueError("`schedule.end` doit être postérieur à `schedule.start`")
        if schedule.freeze is not None and not schedule.start <= schedule.freeze <= schedule.end:
            raise ValueError("`schedule.freeze` doit être compris entre `start` et `end`")
        object.__setattr__(self, "schedule", schedule)

        ids = [c.id for c in self.categories]
        duplicates = {i for i in ids if ids.count(i) > 1}
        if duplicates:
            raise ValueError(f"catégories en double : {', '.join(sorted(duplicates))}")
        return self

    @property
    def flag_prefix(self) -> str | None:
        if not self.flag_format or "{" not in self.flag_format:
            return None
        return self.flag_format.split("{", 1)[0]


# --------------------------------------------------------------------------- challenge.yml


class StaticFlag(StrictModel):
    type: Literal["static"]
    value: str = Field(min_length=1, max_length=512)
    case_sensitive: bool = True


class RegexFlag(StrictModel):
    """Le motif doit couvrir toute la réponse (ancrage implicite)."""

    type: Literal["regex"]
    pattern: str = Field(min_length=1, max_length=512)
    case_sensitive: bool = True

    @field_validator("pattern")
    @classmethod
    def _check_pattern(cls, value: str) -> str:
        try:
            re.compile(value)
        except re.error as exc:
            raise ValueError(f"expression régulière invalide : {exc}") from exc
        return value


FlagSpec = Annotated[StaticFlag | RegexFlag, Field(discriminator="type")]


class ChallengeConfig(StrictModel):
    id: Identifier
    name: str = Field(min_length=1, max_length=128)
    category: Identifier
    difficulty: str | None = None
    authors: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    description: str = "description.md"
    scoring: Scoring | None = None
    flags: list[FlagSpec] = Field(min_length=1)
    files: list[str] = Field(default_factory=list)
    connection: str | None = Field(default=None, max_length=512)
    position: int = 0
