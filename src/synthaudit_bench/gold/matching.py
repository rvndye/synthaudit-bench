"""Deterministic bipartite matching of predictions against gold (specification 5.5).

Scoring compares a prediction set A against a gold set G by a maximum-cardinality
bipartite matching over candidate edges. A candidate edge exists at the detection
level when the supports are equal as sets and the prediction's class is one of the
gold's acceptable classes; the disposition-aware level additionally requires the
disposition to be acceptable; the partial level (secondary metric only) requires
the class to be acceptable and the support Jaccard to reach ``tau_jaccard``.

The matching is made unique by processing gold items and their candidate
predictions in the normative lexicographic key order ``(class, sorted(support),
disposition)`` (Section 5.5), so re-scoring the same inputs always yields the same
matched pairs. This module is pure: it reads only its arguments and never consults
a clock, a global, or any external resource.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from synthaudit_bench.model.ontology import Disposition
from synthaudit_bench.model.tuples import ArtifactTuple, GoldTuple, Support

__all__ = [
    "Candidate",
    "MatchResult",
    "is_candidate_detection",
    "is_candidate_disposition",
    "is_candidate_partial",
    "jaccard",
    "match",
    "support_set",
]

Candidate = Callable[[ArtifactTuple, GoldTuple], bool]


def support_set(support: Support) -> frozenset[str]:
    """Return the support as a set of tokens (a reserved token becomes a singleton)."""
    return frozenset({support}) if isinstance(support, str) else support


def jaccard(left: Support, right: Support) -> float:
    """Return the Jaccard overlap of two supports, comparing them as sets."""
    a = support_set(left)
    b = support_set(right)
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def _disposition_value(disposition: Disposition | None) -> str | None:
    return disposition.value if disposition is not None else None


def is_candidate_detection(prediction: ArtifactTuple, gold: GoldTuple) -> bool:
    """Detection candidate: equal support (as sets) and an acceptable class."""
    return (
        support_set(prediction.support) == support_set(gold.support)
        and prediction.sto_class in gold.classes
    )


def is_candidate_disposition(prediction: ArtifactTuple, gold: GoldTuple) -> bool:
    """Disposition-aware candidate: a detection candidate with an acceptable disposition."""
    if not is_candidate_detection(prediction, gold):
        return False
    value = _disposition_value(prediction.disposition)
    return value is not None and any(value == d.value for d in gold.dispositions)


def is_candidate_partial(prediction: ArtifactTuple, gold: GoldTuple, tau_jaccard: float) -> bool:
    """Partial candidate (secondary metric): acceptable class and support Jaccard >= tau."""
    return (
        prediction.sto_class in gold.classes
        and jaccard(prediction.support, gold.support) >= tau_jaccard
    )


def _gold_key(gold: GoldTuple) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    return (
        tuple(sorted(gold.classes)),
        _support_key(gold.support),
        tuple(sorted(d.value for d in gold.dispositions)),
    )


def _pred_key(prediction: ArtifactTuple) -> tuple[str, tuple[str, ...], str]:
    return (
        prediction.sto_class,
        _support_key(prediction.support),
        _disposition_value(prediction.disposition) or "",
    )


def _support_key(support: Support) -> tuple[str, ...]:
    return (support,) if isinstance(support, str) else tuple(sorted(support))


@dataclass(frozen=True, slots=True)
class MatchResult:
    """The result of matching predictions to gold at one level."""

    matched: tuple[tuple[int, int], ...]
    unmatched_predictions: tuple[int, ...]
    unmatched_gold: tuple[int, ...]


def match(
    predictions: Sequence[ArtifactTuple],
    gold: Sequence[GoldTuple],
    is_candidate: Candidate,
) -> MatchResult:
    """Return the unique maximum-cardinality matching over candidate edges.

    Gold items are processed in ascending normative key order, and each gold
    item's candidate predictions are considered in ascending prediction key order,
    so the augmenting-path (Kuhn) matching it produces is deterministic and unique
    (specification Section 5.5). Each prediction and each gold item is matched at
    most once.
    """
    gold_order = sorted(range(len(gold)), key=lambda g: _gold_key(gold[g]))
    pred_order = sorted(range(len(predictions)), key=lambda p: _pred_key(predictions[p]))
    edges: dict[int, list[int]] = {
        g: [p for p in pred_order if is_candidate(predictions[p], gold[g])]
        for g in range(len(gold))
    }
    match_pred: dict[int, int] = {}

    def _augment(gold_index: int, visited: set[int]) -> bool:
        for pred_index in edges[gold_index]:
            if pred_index in visited:
                continue
            visited.add(pred_index)
            current = match_pred.get(pred_index)
            if current is None or _augment(current, visited):
                match_pred[pred_index] = gold_index
                return True
        return False

    for gold_index in gold_order:
        _augment(gold_index, set())

    matched = tuple(sorted((pred, g) for pred, g in match_pred.items()))
    matched_preds = {pred for pred, _ in matched}
    matched_gold = {g for _, g in matched}
    unmatched_predictions = tuple(p for p in range(len(predictions)) if p not in matched_preds)
    unmatched_gold = tuple(g for g in range(len(gold)) if g not in matched_gold)
    return MatchResult(matched, unmatched_predictions, unmatched_gold)
