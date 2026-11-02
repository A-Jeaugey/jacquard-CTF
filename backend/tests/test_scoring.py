from datetime import UTC, datetime, timedelta

from jacquard.scoring import SolveRecord, TeamRecord, challenge_value, compute_scores

T0 = datetime(2027, 1, 1, tzinfo=UTC)
DYNAMIC = {"type": "dynamic", "initial": 500, "minimum": 100, "decay": 10}


def solve(i: int, team: int, challenge: str, minutes: int) -> SolveRecord:
    return SolveRecord(
        id=i, team_id=team, challenge_id=challenge, created_at=T0 + timedelta(minutes=minutes)
    )


def test_static_value_ignores_solve_count() -> None:
    assert challenge_value({"type": "static", "value": 42}, 0) == 42
    assert challenge_value({"type": "static", "value": 42}, 99) == 42


def test_dynamic_value_decreases_to_minimum() -> None:
    assert challenge_value(DYNAMIC, 0) == 500
    assert challenge_value(DYNAMIC, 1) == 500
    assert challenge_value(DYNAMIC, 6) == 400  # 500 - 400 * (5/10)^2
    assert challenge_value(DYNAMIC, 11) == 100
    assert challenge_value(DYNAMIC, 500) == 100
    values = [challenge_value(DYNAMIC, n) for n in range(1, 20)]
    assert values == sorted(values, reverse=True)


def test_dynamic_value_is_shared_by_all_solvers() -> None:
    teams = [TeamRecord(1, "A"), TeamRecord(2, "B")]
    result = compute_scores({"c": DYNAMIC}, [solve(1, 1, "c", 0), solve(2, 2, "c", 5)], teams)
    assert result.values["c"] == challenge_value(DYNAMIC, 2)
    assert result.team(1).score == result.team(2).score == result.values["c"]  # type: ignore[union-attr]


def test_first_blood_bonus_follows_solve_order() -> None:
    teams = [TeamRecord(1, "A"), TeamRecord(2, "B"), TeamRecord(3, "C")]
    static = {"type": "static", "value": 100}
    solves = [solve(1, 2, "c", 0), solve(2, 1, "c", 1), solve(3, 3, "c", 2)]
    result = compute_scores({"c": static}, solves, teams, first_blood=[50, 20])
    assert result.team(2).score == 150  # type: ignore[union-attr]
    assert result.team(1).score == 120  # type: ignore[union-attr]
    assert result.team(3).score == 100  # type: ignore[union-attr]


def test_hidden_teams_do_not_affect_others() -> None:
    teams = [TeamRecord(1, "Orga", hidden=True), TeamRecord(2, "B")]
    solves = [solve(1, 1, "c", 0), solve(2, 2, "c", 5)]
    result = compute_scores({"c": DYNAMIC}, solves, teams, first_blood=[50])
    assert result.solve_counts["c"] == 1
    assert result.team(2).score == 550  # type: ignore[union-attr]
    assert result.team(2).rank == 1  # type: ignore[union-attr]
    assert result.team(1).rank is None  # type: ignore[union-attr]


def test_tie_break_favours_earliest_last_solve() -> None:
    teams = [TeamRecord(1, "Lent"), TeamRecord(2, "Rapide"), TeamRecord(3, "Zéro")]
    static = {"type": "static", "value": 100}
    solves = [solve(1, 1, "c", 30), solve(2, 2, "c", 10)]
    result = compute_scores({"c": static}, solves, teams)
    assert [t.name for t in result.teams] == ["Rapide", "Lent", "Zéro"]
    assert [t.rank for t in result.teams] == [1, 2, 3]


def test_unknown_challenges_and_teams_are_ignored() -> None:
    result = compute_scores(
        {"c": {"type": "static", "value": 10}},
        [solve(1, 1, "retire", 0), solve(2, 99, "c", 0)],
        [TeamRecord(1, "A")],
    )
    assert result.team(1).score == 0  # type: ignore[union-attr]
    assert result.solve_counts["c"] == 0


def test_hint_penalties_are_deducted() -> None:
    teams = [TeamRecord(1, "A"), TeamRecord(2, "B")]
    static = {"type": "static", "value": 100}
    result = compute_scores(
        {"c": static}, [solve(1, 1, "c", 0), solve(2, 2, "c", 1)], teams, penalties={1: 30, 99: 5}
    )
    assert result.team(1).score == 70  # type: ignore[union-attr]
    assert result.team(1).penalty == 30  # type: ignore[union-attr]
    assert [t.name for t in result.teams] == ["B", "A"]


def test_penalty_can_make_score_negative() -> None:
    result = compute_scores({}, [], [TeamRecord(1, "A")], penalties={1: 10})
    assert result.team(1).score == -10  # type: ignore[union-attr]
