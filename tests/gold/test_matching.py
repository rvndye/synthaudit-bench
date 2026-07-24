"""Unit tests for deterministic prediction-to-gold matching (specification 5.5)."""

from __future__ import annotations

import pytest
from _goldhelpers import gold, pred

from synthaudit_bench.gold.matching import (
    is_candidate_detection,
    is_candidate_disposition,
    is_candidate_partial,
    jaccard,
    match,
    support_set,
)
from synthaudit_bench.model.tuples import ROWS


def test_support_set_token_and_columns() -> None:
    assert support_set(ROWS) == frozenset({ROWS})
    assert support_set(frozenset({"a", "b"})) == frozenset({"a", "b"})


@pytest.mark.parametrize(
    "left,right,expected",
    [
        (frozenset({"a", "b"}), frozenset({"a", "b"}), 1.0),
        (frozenset({"a", "b"}), frozenset({"b", "c"}), 1 / 3),
        (frozenset({"a"}), frozenset({"z"}), 0.0),
        (ROWS, ROWS, 1.0),
        (frozenset(), frozenset(), 0.0),
    ],
)
def test_jaccard(left: object, right: object, expected: float) -> None:
    assert jaccard(left, right) == pytest.approx(expected)  # type: ignore[arg-type]


def test_candidate_detection() -> None:
    g = gold(("a", "b"), ("STO-A01",))
    assert is_candidate_detection(pred(("a", "b"), "STO-A01"), g) is True
    assert is_candidate_detection(pred(("a", "c"), "STO-A01"), g) is False  # support differs
    assert is_candidate_detection(pred(("a", "b"), "STO-A02"), g) is False  # class not accepted


def test_candidate_disposition() -> None:
    g = gold(("a", "b"), ("STO-A01",), ("structural_constraint",))
    ok = pred(("a", "b"), "STO-A01", disposition="structural_constraint")
    assert is_candidate_disposition(ok, g) is True
    assert is_candidate_disposition(pred(("a", "b"), "STO-A01"), g) is False  # no disposition
    wrong = pred(("a", "b"), "STO-A01", disposition="target_leakage")
    assert is_candidate_disposition(wrong, g) is False
    assert (
        is_candidate_disposition(
            pred(("a", "c"), "STO-A01", disposition="structural_constraint"), g
        )
        is False
    )


def test_candidate_partial() -> None:
    g = gold(("a", "b", "c", "d"), ("STO-A01",))
    assert is_candidate_partial(pred(("a", "b", "c"), "STO-A01"), g, 0.5) is True  # jaccard 3/4
    assert is_candidate_partial(pred(("a",), "STO-A01"), g, 0.5) is False  # jaccard 1/4
    assert is_candidate_partial(pred(("a", "b", "c"), "STO-A02"), g, 0.5) is False  # class


def test_match_basic_and_unmatched() -> None:
    preds = [pred(("a",), "STO-S02"), pred(("x",), "STO-S02")]
    golds = [gold(("a",), ("STO-S02",))]
    result = match(preds, golds, is_candidate_detection)
    assert result.matched == ((0, 0),)
    assert result.unmatched_predictions == (1,)
    assert result.unmatched_gold == ()


def test_match_maximum_cardinality_via_augmenting_path() -> None:
    # gold0 matches only pred "a"; gold1 matches "a" and "b". A greedy assignment
    # that gives "a" to gold1 must reassign so both gold items match.
    preds = [pred(("a",), "STO-A01"), pred(("b",), "STO-A02")]
    golds = [
        gold(("a",), ("STO-A01",)),  # only pred 0
        gold(("b",), ("STO-A01", "STO-A02")),  # pred 1 (and, by class, nothing else here)
    ]
    result = match(preds, golds, is_candidate_detection)
    assert len(result.matched) == 2
    assert result.unmatched_predictions == ()
    assert result.unmatched_gold == ()


def test_match_is_deterministic() -> None:
    preds = [pred(("a",), "STO-S02"), pred(("a",), "STO-S02")]
    golds = [gold(("a",), ("STO-S02",))]
    first = match(preds, golds, is_candidate_detection)
    second = match(preds, golds, is_candidate_detection)
    assert first == second
    assert len(first.matched) == 1  # one gold, one match despite two identical preds


def test_match_leaves_gold_unmatched_when_no_augmenting_path() -> None:
    # two gold items compete for the single available prediction; one stays unmatched
    preds = [pred(("a",), "STO-S02")]
    golds = [gold(("a",), ("STO-S02",)), gold(("a",), ("STO-S02",))]
    result = match(preds, golds, is_candidate_detection)
    assert len(result.matched) == 1
    assert len(result.unmatched_gold) == 1


def test_match_empty() -> None:
    result = match([], [], is_candidate_detection)
    assert result.matched == ()
    assert result.unmatched_predictions == ()
    assert result.unmatched_gold == ()
