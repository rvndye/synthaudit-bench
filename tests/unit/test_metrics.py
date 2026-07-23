"""Unit tests for the scoring metrics table and its value objects."""

from __future__ import annotations

import dataclasses

import pytest

from synthaudit_bench.model.metrics import (
    AggregateScores,
    CoverageReport,
    DatasetMetrics,
    MetricsTable,
    Score,
)

_S = Score(precision=0.8, recall=0.6, f1=0.686, tp=6, fp=1, fn=4)
_AGG = AggregateScores(micro=_S, macro_class_f1=0.5, macro_dataset_f1=0.55)


def _table(**overrides: object) -> MetricsTable:
    base: dict[str, object] = {
        "split": "public-dev",
        "detection": _AGG,
        "disposition_aware": _AGG,
        "coverage": CoverageReport(abstain_hit=2, abstain_other=1),
    }
    base.update(overrides)
    return MetricsTable(**base)  # type: ignore[arg-type]


def test_score_round_trip() -> None:
    assert Score.from_mapping(_S.to_mapping()) == _S
    bare = Score(precision=0.0, recall=0.0, f1=0.0)
    assert bare.to_mapping()["tp"] == 0
    assert Score.from_mapping(bare.to_mapping()) == bare


def test_aggregate_scores_round_trip() -> None:
    assert AggregateScores.from_mapping(_AGG.to_mapping()) == _AGG


def test_coverage_report_round_trip_minimal_and_full() -> None:
    minimal = CoverageReport()
    assert minimal.to_mapping() == {
        "abstain_hit": 0,
        "abstain_other": 0,
        "gold_type_recall": {},
    }
    assert CoverageReport.from_mapping(minimal.to_mapping()) == minimal
    full = CoverageReport(
        abstain_hit=3,
        abstain_other=2,
        gold_type_recall={"objective": 0.9, "adjudicated": 0.4},
        objective_gold_recall=0.9,
        adjudicated_gold_recall=0.4,
    )
    assert CoverageReport.from_mapping(full.to_mapping()) == full
    assert list(full.to_mapping()["gold_type_recall"]) == ["adjudicated", "objective"]


def test_dataset_metrics_round_trip_with_and_without_partial() -> None:
    plain = DatasetMetrics(dataset_id="grid", detection=_S, disposition_aware=_S)
    assert "partial_credit" not in plain.to_mapping()
    assert DatasetMetrics.from_mapping(plain.to_mapping()) == plain
    withp = DatasetMetrics(dataset_id="grid", detection=_S, disposition_aware=_S, partial_credit=_S)
    assert DatasetMetrics.from_mapping(withp.to_mapping()) == withp


def test_metrics_table_minimal_and_full_round_trip() -> None:
    assert MetricsTable.from_mapping(_table().to_mapping()) == _table()
    full = _table(
        per_class={"STO-A01": _S, "STO-A07": _S},
        per_disposition={"target_leakage": _S},
        per_dataset=(DatasetMetrics(dataset_id="grid", detection=_S, disposition_aware=_S),),
        partial_credit=_AGG,
    )
    assert MetricsTable.from_mapping(full.to_mapping()) == full


def test_per_dataset_normalized_to_sorted_order() -> None:
    table = _table(
        per_dataset=(
            DatasetMetrics(dataset_id="zebra", detection=_S, disposition_aware=_S),
            DatasetMetrics(dataset_id="alpha", detection=_S, disposition_aware=_S),
        )
    )
    assert [d.dataset_id for d in table.per_dataset] == ["alpha", "zebra"]


def test_content_hash_is_content_addressed_and_key_order_stable() -> None:
    a = _table()
    b = _table(split="held-out")
    assert a.content_hash() != b.content_hash()
    c1 = _table(per_class={"STO-A01": _S, "STO-A07": _S})
    c2 = _table(per_class={"STO-A07": _S, "STO-A01": _S})
    assert c1.content_hash() == c2.content_hash()
    assert len(a.content_hash()) == 64
    assert isinstance(a.to_canonical(), bytes)


def test_metrics_table_is_immutable() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        _table().split = "x"  # type: ignore[misc]
