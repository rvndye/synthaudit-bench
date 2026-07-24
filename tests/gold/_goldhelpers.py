"""Helpers for gold-module tests: concise builders for predictions and gold."""

from __future__ import annotations

from collections.abc import Iterable

from synthaudit_bench.model.ontology import Disposition, GoldType
from synthaudit_bench.model.tuples import ArtifactTuple, GoldTuple


def pred(
    support: Iterable[str] | str,
    sto_class: str,
    *,
    disposition: str | None = None,
    confidence: float | None = None,
) -> ArtifactTuple:
    support_value = support if isinstance(support, str) else frozenset(support)
    return ArtifactTuple(
        support=support_value,
        sto_class=sto_class,
        disposition=Disposition(disposition) if disposition is not None else None,
        confidence=confidence,
    )


def gold(
    support: Iterable[str] | str,
    classes: Iterable[str],
    dispositions: Iterable[str] = ("not_applicable",),
    *,
    gold_type: str = "objective",
    optional: bool = False,
) -> GoldTuple:
    support_value = support if isinstance(support, str) else frozenset(support)
    return GoldTuple(
        support=support_value,
        classes=frozenset(classes),
        dispositions=frozenset(Disposition(d) for d in dispositions),
        gold_type=GoldType(gold_type),
        optional=optional,
        evidence="evidence",
    )
