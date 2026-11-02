from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from jacquard.packs.schema import RULE_ADAPTER, dump_rule, load_rule
from jacquard.rules import (
    ChallengeMeta,
    TeamContext,
    Unlockable,
    evaluate,
    reachable,
    references,
)

PARIS = ZoneInfo("Europe/Paris")
START = datetime(2027, 3, 14, 13, 0, tzinfo=UTC)  # 14:00 à Paris
END = START + timedelta(hours=6)
CATALOG = {
    "a": ChallengeMeta("web", frozenset({"debutant"}), "facile"),
    "b": ChallengeMeta("web", frozenset(), "moyen"),
    "c": ChallengeMeta("crypto", frozenset({"debutant"}), "facile"),
}


def ctx(**overrides: Any) -> TeamContext:
    values: dict[str, Any] = {
        "solved": frozenset(),
        "catalog": CATALOG,
        "score": 0,
        "items": frozenset(),
        "hints_used": frozenset(),
        "now": START + timedelta(minutes=10),
        "start": START,
        "tz": PARIS,
    }
    values.update(overrides)
    values["solved"] = frozenset(values["solved"])
    values["items"] = frozenset(values["items"])
    values["hints_used"] = frozenset(values["hints_used"])
    return TeamContext(**values)


def rule(data: dict[str, Any]) -> Any:
    return RULE_ADAPTER.validate_python(data)


def test_no_rule_is_always_true() -> None:
    assert evaluate(None, ctx())


@pytest.mark.parametrize(
    ("data", "context", "expected"),
    [
        ({"solved": "a"}, {"solved": {"a"}}, True),
        ({"solved": "a"}, {"solved": {"b"}}, False),
        ({"solved_count": {"gte": 2}}, {"solved": {"a", "c"}}, True),
        ({"solved_count": {"category": "web", "gte": 2}}, {"solved": {"a", "c"}}, False),
        ({"solved_count": {"category": "web", "gte": 2}}, {"solved": {"a", "b"}}, True),
        ({"solved_count": {"tag": "debutant", "gte": 2}}, {"solved": {"a", "c"}}, True),
        ({"solved_count": {"difficulty": "moyen", "gte": 1}}, {"solved": {"a"}}, False),
        ({"score": {"gte": 300}}, {"score": 300}, True),
        ({"score": {"gte": 300}}, {"score": 299}, False),
        ({"item": "cle"}, {"items": {"cle"}}, True),
        ({"item": "cle"}, {}, False),
        ({"hint_used": "h1"}, {"hints_used": {"h1"}}, True),
        ({"time": {"elapsed_minutes": 10}}, {}, True),
        ({"time": {"elapsed_minutes": 11}}, {}, False),
        # Date sans fuseau : heure de Paris. 14:10 à Paris = début + 10 min.
        ({"time": {"after": "2027-03-14T14:10:00"}}, {}, True),
        ({"time": {"after": "2027-03-14T14:11:00"}}, {}, False),
        ({"time": {"before": "2027-03-14T14:11:00"}}, {}, True),
        ({"all": [{"solved": "a"}, {"item": "cle"}]}, {"solved": {"a"}}, False),
        ({"all": [{"solved": "a"}, {"item": "cle"}]}, {"solved": {"a"}, "items": {"cle"}}, True),
        ({"any": [{"solved": "a"}, {"item": "cle"}]}, {"items": {"cle"}}, True),
        ({"not": {"solved": "a"}}, {}, True),
        ({"not": {"solved": "a"}}, {"solved": {"a"}}, False),
        (
            {"any": [{"all": [{"solved": "a"}, {"solved": "b"}]}, {"score": {"gte": 1}}]},
            {"score": 5},
            True,
        ),
    ],
)
def test_evaluate(data: dict[str, Any], context: dict[str, Any], expected: bool) -> None:
    assert evaluate(rule(data), ctx(**context)) is expected


@pytest.mark.parametrize(
    "data",
    [
        {"solvd": "a"},
        {"solved": "a", "item": "b"},
        {},
        {"all": []},
        {"time": {"after": "2027-01-01T00:00:00", "elapsed_minutes": 3}},
        {"time": {}},
        {"solved_count": {"gte": 0}},
        {"solved": "Majuscules"},
    ],
)
def test_invalid_rules(data: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        rule(data)


def test_rule_roundtrip() -> None:
    data = {
        "all": [
            {"not": {"item": "k"}},
            {"any": [{"solved": "a"}, {"time": {"elapsed_minutes": 5}}]},
        ]
    }
    assert dump_rule(load_rule(data)) == data


def test_references() -> None:
    found = references(
        rule(
            {
                "all": [
                    {"solved": "a"},
                    {"not": {"item": "k"}},
                    {"solved_count": {"category": "web", "difficulty": "facile", "gte": 1}},
                    {"hint_used": "h"},
                ]
            }
        )
    )
    assert found.challenges == {"a"}
    assert found.items == {"k"}
    assert found.categories == {"web"}
    assert found.difficulties == {"facile"}
    assert found.hints == {"h"}


def _reach(*challenges: Unlockable) -> set[str]:
    return set(reachable(list(challenges), CATALOG, start=START, end=END, tz=PARIS).solved)


def test_reachability_follows_chains_and_items() -> None:
    result = _reach(
        Unlockable("a", None, max_points=100, grants=frozenset({"cle"})),
        Unlockable("b", rule({"item": "cle"})),
        Unlockable("c", rule({"all": [{"solved": "b"}, {"score": {"gte": 100}}]})),
    )
    assert result == {"a", "b", "c"}


def test_reachability_detects_cycles_and_impossible_conditions() -> None:
    result = _reach(
        Unlockable("a", rule({"solved": "b"})),
        Unlockable("b", rule({"solved": "a"})),
        Unlockable("c", rule({"score": {"gte": 1000}}), max_points=10),
        Unlockable("d", rule({"time": {"after": "2030-01-01T00:00:00"}})),
        Unlockable("e", rule({"solved": "e"})),
    )
    assert result == set()


def test_reachability_through_hints() -> None:
    result = _reach(
        Unlockable("a", None, hints={"h": rule({"time": {"elapsed_minutes": 60}})}),
        Unlockable("b", rule({"hint_used": "h"})),
    )
    assert result == {"a", "b"}
