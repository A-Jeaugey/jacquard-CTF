"""Schéma des fichiers d'un pack d'événement.

Les modèles refusent les champs inconnus : une faute de frappe dans un YAML (ou un champ
pas encore pris en charge par cette version) est signalée à la validation plutôt
qu'ignorée silencieusement.
"""

import re
from datetime import datetime
from typing import Annotated, Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    BaseModel,
    ConfigDict,
    Discriminator,
    Field,
    Tag,
    TypeAdapter,
    field_validator,
    model_validator,
)

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


# --------------------------------------------------------------------------- règles
#
# Une règle est un objet YAML à une seule clé : une primitive (`solved`, `item`...) ou un
# combinateur (`all`, `any`, `not`). Voir docs/conception-plateforme.md, §4.


class SolvedRule(StrictModel):
    solved: Identifier


class SolvedCount(StrictModel):
    category: Identifier | None = None
    tag: str | None = None
    difficulty: str | None = None
    gte: int = Field(ge=1)


class SolvedCountRule(StrictModel):
    solved_count: SolvedCount


class ScoreCondition(StrictModel):
    gte: int


class ScoreRule(StrictModel):
    score: ScoreCondition


class ItemRule(StrictModel):
    item: Identifier


class HintUsedRule(StrictModel):
    hint_used: Identifier


class TimeCondition(StrictModel):
    """Exactement une condition. Les dates sans fuseau suivent celui de l'événement."""

    after: datetime | None = None
    before: datetime | None = None
    elapsed_minutes: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _exactly_one(self) -> "TimeCondition":
        given = [v for v in (self.after, self.before, self.elapsed_minutes) if v is not None]
        if len(given) != 1:
            raise ValueError("indiquer exactement une condition : after, before ou elapsed_minutes")
        return self


class TimeRule(StrictModel):
    time: TimeCondition


class AllRule(StrictModel):
    all: "list[Rule]" = Field(min_length=1)


class AnyRule(StrictModel):
    any: "list[Rule]" = Field(min_length=1)


class NotRule(StrictModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    not_: "Rule" = Field(alias="not")


_RULE_TAGS: dict[type[BaseModel], str] = {
    SolvedRule: "solved",
    SolvedCountRule: "solved_count",
    ScoreRule: "score",
    ItemRule: "item",
    HintUsedRule: "hint_used",
    TimeRule: "time",
    AllRule: "all",
    AnyRule: "any",
    NotRule: "not",
}


def _rule_tag(value: Any) -> str | None:
    if isinstance(value, dict):
        return next(iter(value)) if len(value) == 1 else None
    return _RULE_TAGS.get(type(value))


Rule = Annotated[
    Annotated[SolvedRule, Tag("solved")]
    | Annotated[SolvedCountRule, Tag("solved_count")]
    | Annotated[ScoreRule, Tag("score")]
    | Annotated[ItemRule, Tag("item")]
    | Annotated[HintUsedRule, Tag("hint_used")]
    | Annotated[TimeRule, Tag("time")]
    | Annotated[AllRule, Tag("all")]
    | Annotated[AnyRule, Tag("any")]
    | Annotated[NotRule, Tag("not")],
    Discriminator(
        _rule_tag,
        custom_error_type="invalid_rule",
        custom_error_message=(
            "règle invalide : un seul mot-clé parmi solved, solved_count, score, item, "
            "hint_used, time, all, any, not"
        ),
    ),
]

for _model in (AllRule, AnyRule, NotRule):
    _model.model_rebuild()

RULE_ADAPTER: TypeAdapter[Rule] = TypeAdapter(Rule)


def dump_rule(rule: Rule | None) -> dict[str, Any] | None:
    """Forme JSON d'une règle, pour la stocker en base."""
    if rule is None:
        return None
    return RULE_ADAPTER.dump_python(rule, mode="json", by_alias=True, exclude_none=True)  # type: ignore[no-any-return]


def load_rule(data: dict[str, Any] | None) -> Rule | None:
    return None if data is None else RULE_ADAPTER.validate_python(data)


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


class ItemDefinition(StrictModel):
    """Objet que les équipes peuvent obtenir (clé, fragment, badge...)."""

    id: Identifier
    name: str = Field(min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=512)


class HintPolicy(StrictModel):
    # Si vrai, une équipe ne peut acheter un indice que si son score couvre son coût.
    # Faux par défaut : un débutant à zéro point doit pouvoir être aidé.
    require_points: bool = False


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
    # Adresse des services de défis, substituée à « {challenge_host} » dans `connection`.
    challenge_host: str | None = Field(
        default=None, max_length=253, pattern=r"^[A-Za-z0-9.\-:\[\]]+$"
    )
    items: list[ItemDefinition] = Field(default_factory=list)
    hints: HintPolicy = HintPolicy()

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
        item_ids = [i.id for i in self.items]
        duplicates = {i for i in item_ids if item_ids.count(i) > 1}
        if duplicates:
            raise ValueError(f"objets en double : {', '.join(sorted(duplicates))}")
        return self

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

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


class HintSpec(StrictModel):
    id: Identifier
    text: str = Field(min_length=1, max_length=4000)
    cost: int = Field(default=0, ge=0)
    available: Rule | None = None


class GrantItem(StrictModel):
    grant_item: Identifier


class Notify(StrictModel):
    notify: str = Field(min_length=1, max_length=2000)


OnSolveAction = GrantItem | Notify


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
    unlock: Rule | None = None
    when_locked: Literal["hidden", "teaser"] = "hidden"
    locked_message: str | None = Field(default=None, max_length=256)
    hints: list[HintSpec] = Field(default_factory=list)
    on_solve: list[OnSolveAction] = Field(default_factory=list)


# --------------------------------------------------------------------------- story/*.md


class StoryConfig(StrictModel):
    """En-tête YAML d'un chapitre d'histoire."""

    id: Identifier
    title: str = Field(min_length=1, max_length=128)
    order: int = 0
    unlock: Rule | None = None
    # Visible par tous, même sans compte et avant le début (prologue).
    public: bool = False

    @model_validator(mode="after")
    def _public_has_no_rule(self) -> "StoryConfig":
        if self.public and self.unlock is not None:
            raise ValueError("un chapitre public ne peut pas avoir de règle de déblocage")
        return self
