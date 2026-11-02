"""Calcul des scores. Fonctions pures, sans accès à la base.

Règles :
- valeur statique, ou dynamique (décroît avec le nombre d'équipes ayant résolu le défi ;
  toutes les équipes reçoivent la valeur actuelle, y compris celles qui ont résolu tôt) ;
- bonus de premier sang selon le rang de résolution, non rétroactif ;
- les équipes masquées (orga, tests) ne comptent ni dans la décroissance ni dans les bonus ;
- le coût des indices achetés est déduit du score ;
- départage : à score égal, l'équipe dont la dernière résolution est la plus ancienne gagne.
"""

import math
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class SolveRecord:
    id: int
    team_id: int
    challenge_id: str
    created_at: datetime


@dataclass(frozen=True)
class TeamRecord:
    id: int
    name: str
    hidden: bool = False


@dataclass
class TeamScore:
    team_id: int
    name: str
    score: int
    solves: int
    last_solve_at: datetime | None
    rank: int | None = None
    hidden: bool = False
    penalty: int = 0  # coût total des indices achetés
    solved: dict[str, int] = field(default_factory=dict)  # défi -> points obtenus


def challenge_value(scoring: Mapping[str, Any], solve_count: int) -> int:
    """Valeur d'un défi résolu par `solve_count` équipes comptabilisées.

    En mode dynamique, la valeur suit une parabole de `initial` à `minimum`, atteinte
    lorsque `decay` équipes ont résolu le défi après la première.
    """
    if scoring["type"] == "static":
        return int(scoring["value"])
    initial, minimum, decay = (
        int(scoring["initial"]),
        int(scoring["minimum"]),
        int(scoring["decay"]),
    )
    extra = max(solve_count - 1, 0)
    value = initial + (minimum - initial) * (extra / decay) ** 2
    return max(minimum, math.ceil(value))


def _order(solve: SolveRecord) -> tuple[datetime, int]:
    return (solve.created_at, solve.id)


@dataclass(frozen=True)
class ScoringResult:
    values: dict[str, int]
    solve_counts: dict[str, int]
    teams: list[TeamScore]

    def team(self, team_id: int) -> TeamScore | None:
        return next((t for t in self.teams if t.team_id == team_id), None)


def compute_scores(
    challenges: Mapping[str, Mapping[str, Any]],
    solves: Iterable[SolveRecord],
    teams: Sequence[TeamRecord],
    first_blood: Sequence[int] = (),
    penalties: Mapping[int, int] | None = None,
) -> ScoringResult:
    hidden = {t.id for t in teams if t.hidden}
    known = {t.id for t in teams}
    relevant = sorted(
        (s for s in solves if s.challenge_id in challenges and s.team_id in known), key=_order
    )

    by_challenge: dict[str, list[SolveRecord]] = defaultdict(list)
    for solve in relevant:
        if solve.team_id not in hidden:
            by_challenge[solve.challenge_id].append(solve)

    solve_counts = {cid: len(by_challenge.get(cid, [])) for cid in challenges}
    values = {cid: challenge_value(cfg, solve_counts[cid]) for cid, cfg in challenges.items()}

    bonus: dict[int, int] = {}
    for counted in by_challenge.values():
        for rank, solve in enumerate(counted[: len(first_blood)]):
            bonus[solve.id] = first_blood[rank]

    scores = {
        t.id: TeamScore(
            team_id=t.id, name=t.name, score=0, solves=0, last_solve_at=None, hidden=t.hidden
        )
        for t in teams
    }
    for solve in relevant:
        entry = scores[solve.team_id]
        points = values[solve.challenge_id] + bonus.get(solve.id, 0)
        entry.solved[solve.challenge_id] = points
        entry.score += points
        entry.solves += 1
        entry.last_solve_at = solve.created_at
    for team_id, cost in (penalties or {}).items():
        if team_id in scores:
            scores[team_id].penalty += cost
            scores[team_id].score -= cost

    def sort_key(entry: TeamScore) -> tuple[int, int, float, int]:
        has_solve = 0 if entry.last_solve_at is not None else 1
        moment = entry.last_solve_at.timestamp() if entry.last_solve_at else 0.0
        return (-entry.score, has_solve, moment, entry.team_id)

    ordered = sorted(scores.values(), key=sort_key)
    rank = 0
    for entry in ordered:
        if not entry.hidden:
            rank += 1
            entry.rank = rank
    return ScoringResult(values=values, solve_counts=solve_counts, teams=ordered)
