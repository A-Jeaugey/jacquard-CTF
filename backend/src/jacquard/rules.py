"""Moteur de règles. Fonctions pures, sans accès à la base.

Deux évaluations :
- `evaluate` : la règle est-elle vraie pour cette équipe, maintenant ?
- `possible` : la règle peut-elle devenir vraie un jour ? Évaluation optimiste, utilisée
  par le validateur de pack pour détecter les défis impossibles à débloquer.
"""

from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta, tzinfo

from jacquard.packs.schema import (
    AllRule,
    AnyRule,
    HintUsedRule,
    ItemRule,
    NotRule,
    Rule,
    ScoreRule,
    SolvedCountRule,
    SolvedRule,
    TimeRule,
)


@dataclass(frozen=True)
class ChallengeMeta:
    category: str
    tags: frozenset[str] = frozenset()
    difficulty: str | None = None


@dataclass(frozen=True)
class TeamContext:
    solved: frozenset[str]
    catalog: Mapping[str, ChallengeMeta]
    score: int
    items: frozenset[str]
    hints_used: frozenset[str]
    now: datetime
    start: datetime
    tz: tzinfo


def _localize(moment: datetime, tz: tzinfo) -> datetime:
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=tz)


def _count_solved(
    rule: SolvedCountRule, solved: Iterable[str], catalog: Mapping[str, ChallengeMeta]
) -> int:
    condition = rule.solved_count
    count = 0
    for challenge_id in solved:
        meta = catalog.get(challenge_id)
        if meta is None:
            continue
        if condition.category is not None and meta.category != condition.category:
            continue
        if condition.tag is not None and condition.tag not in meta.tags:
            continue
        if condition.difficulty is not None and meta.difficulty != condition.difficulty:
            continue
        count += 1
    return count


def evaluate(rule: Rule | None, ctx: TeamContext) -> bool:
    if rule is None:
        return True
    match rule:
        case SolvedRule():
            return rule.solved in ctx.solved
        case SolvedCountRule():
            return _count_solved(rule, ctx.solved, ctx.catalog) >= rule.solved_count.gte
        case ScoreRule():
            return ctx.score >= rule.score.gte
        case ItemRule():
            return rule.item in ctx.items
        case HintUsedRule():
            return rule.hint_used in ctx.hints_used
        case TimeRule():
            condition = rule.time
            if condition.after is not None:
                return ctx.now >= _localize(condition.after, ctx.tz)
            if condition.before is not None:
                return ctx.now < _localize(condition.before, ctx.tz)
            assert condition.elapsed_minutes is not None
            return ctx.now >= ctx.start + timedelta(minutes=condition.elapsed_minutes)
        case AllRule():
            return all(evaluate(child, ctx) for child in rule.all)
        case AnyRule():
            return any(evaluate(child, ctx) for child in rule.any)
        case NotRule():
            return not evaluate(rule.not_, ctx)
    raise TypeError(f"règle inconnue : {rule!r}")  # pragma: no cover


# --------------------------------------------------------------------------- références


@dataclass
class References:
    challenges: set[str] = field(default_factory=set)
    categories: set[str] = field(default_factory=set)
    difficulties: set[str] = field(default_factory=set)
    items: set[str] = field(default_factory=set)
    hints: set[str] = field(default_factory=set)


def _walk(rule: Rule) -> Iterator[Rule]:
    yield rule
    match rule:
        case AllRule():
            for child in rule.all:
                yield from _walk(child)
        case AnyRule():
            for child in rule.any:
                yield from _walk(child)
        case NotRule():
            yield from _walk(rule.not_)


def references(rule: Rule | None) -> References:
    """Identifiants mentionnés par une règle, pour vérifier qu'ils existent."""
    found = References()
    if rule is None:
        return found
    for node in _walk(rule):
        match node:
            case SolvedRule():
                found.challenges.add(node.solved)
            case SolvedCountRule():
                if node.solved_count.category:
                    found.categories.add(node.solved_count.category)
                if node.solved_count.difficulty:
                    found.difficulties.add(node.solved_count.difficulty)
            case ItemRule():
                found.items.add(node.item)
            case HintUsedRule():
                found.hints.add(node.hint_used)
    return found


@dataclass
class Prerequisites:
    """Ce qu'une règle exige, lisible par un joueur : les défis à résoudre avant et l'heure
    d'ouverture. Les branches `not` sont ignorées (elles retirent, n'ouvrent pas)."""

    challenges: list[str] = field(default_factory=list)
    opens_at: datetime | None = None


def prerequisites(rule: Rule | None, start: datetime, tz: tzinfo) -> Prerequisites:
    found = Prerequisites()

    def visit(node: Rule) -> None:
        match node:
            case AllRule():
                for child in node.all:
                    visit(child)
            case AnyRule():
                for child in node.any:
                    visit(child)
            case SolvedRule():
                if node.solved not in found.challenges:
                    found.challenges.append(node.solved)
            case TimeRule():
                moment = None
                if node.time.elapsed_minutes is not None:
                    moment = start + timedelta(minutes=node.time.elapsed_minutes)
                elif node.time.after is not None:
                    moment = _localize(node.time.after, tz)
                if moment is not None and (found.opens_at is None or moment > found.opens_at):
                    found.opens_at = moment

    if rule is not None:
        visit(rule)
    return found


# --------------------------------------------------------------------------- atteignabilité


@dataclass(frozen=True)
class OptimisticContext:
    """Meilleur cas : tout ce qui est atteignable a été résolu, acheté ou obtenu."""

    solved: frozenset[str]
    catalog: Mapping[str, ChallengeMeta]
    max_score: int
    items: frozenset[str]
    hints: frozenset[str]
    start: datetime
    end: datetime
    tz: tzinfo


def possible(rule: Rule | None, ctx: OptimisticContext) -> bool:
    if rule is None:
        return True
    match rule:
        case SolvedRule():
            return rule.solved in ctx.solved
        case SolvedCountRule():
            return _count_solved(rule, ctx.solved, ctx.catalog) >= rule.solved_count.gte
        case ScoreRule():
            return ctx.max_score >= rule.score.gte
        case ItemRule():
            return rule.item in ctx.items
        case HintUsedRule():
            return rule.hint_used in ctx.hints
        case TimeRule():
            condition = rule.time
            if condition.after is not None:
                return _localize(condition.after, ctx.tz) < ctx.end
            if condition.before is not None:
                return _localize(condition.before, ctx.tz) > ctx.start
            assert condition.elapsed_minutes is not None
            return ctx.start + timedelta(minutes=condition.elapsed_minutes) < ctx.end
        case AllRule():
            return all(possible(child, ctx) for child in rule.all)
        case AnyRule():
            return any(possible(child, ctx) for child in rule.any)
        case NotRule():
            # Une négation ne se raisonne pas de façon optimiste : on la suppose possible.
            return True
    raise TypeError(f"règle inconnue : {rule!r}")  # pragma: no cover


@dataclass(frozen=True)
class Unlockable:
    id: str
    unlock: Rule | None
    max_points: int = 0
    grants: frozenset[str] = frozenset()
    hints: Mapping[str, Rule | None] = field(default_factory=dict)


def reachable(
    challenges: Iterable[Unlockable],
    catalog: Mapping[str, ChallengeMeta],
    *,
    start: datetime,
    end: datetime,
    tz: tzinfo,
) -> OptimisticContext:
    """Point fixe : agrandit l'ensemble des défis atteignables jusqu'à stabilité."""
    all_challenges = list(challenges)
    pending = {c.id: c for c in all_challenges}
    solved: set[str] = set()
    items: set[str] = set()
    hints: set[str] = set()
    max_score = 0

    def context() -> OptimisticContext:
        return OptimisticContext(
            solved=frozenset(solved),
            catalog=catalog,
            max_score=max_score,
            items=frozenset(items),
            hints=frozenset(hints),
            start=start,
            end=end,
            tz=tz,
        )

    changed = True
    while changed:
        changed = False
        ctx = context()
        for challenge_id, challenge in list(pending.items()):
            if possible(challenge.unlock, ctx):
                del pending[challenge_id]
                solved.add(challenge_id)
                items |= challenge.grants
                max_score += challenge.max_points
                changed = True
        # Les indices des défis atteignables deviennent achetables si leur règle le permet.
        ctx = context()
        for challenge in all_challenges:
            if challenge.id in solved:
                for hint_id, rule in challenge.hints.items():
                    if hint_id not in hints and possible(rule, ctx):
                        hints.add(hint_id)
                        changed = True
    return context()
