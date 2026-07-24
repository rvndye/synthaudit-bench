"""Unit tests for gold scoring: counts, metrics, aggregation, validation."""

from __future__ import annotations

from typing import Any

import pytest
from _goldhelpers import gold, pred

from synthaudit_bench.gold import (
    Counts,
    detector_summary,
    evaluate,
    score_predictions,
    scoring,
    validate_gold,
    validate_metrics,
)
from synthaudit_bench.gold.errors import InvalidGoldError, MetricsError
from synthaudit_bench.model.results import AuditResult, DetectorInfo, ErrorRecord
from synthaudit_bench.model.tuples import ROWS


def test_counts_score_zero_and_normal() -> None:
    assert Counts().score().f1 == 0.0
    score = Counts(tp=3, fp=1, fn=1).score()
    assert score.precision == pytest.approx(0.75)
    assert score.recall == pytest.approx(0.75)
    assert score.f1 == pytest.approx(0.75)


def _result(dataset_id: str, tuples: Any, *, error: ErrorRecord | None = None) -> AuditResult:
    return AuditResult(
        dataset_id=dataset_id,
        dataset_sha256="a" * 64,
        detector=DetectorInfo("t", "1"),
        tuples=tuple(tuples),
        error=error,
    )


def test_score_predictions_worked_example() -> None:
    golds = [
        gold(("stab", "stabf"), ("STO-A07",), ("target_leakage",)),
        gold(("p1", "p2", "p3", "p4"), ("STO-A02", "STO-A01"), ("structural_constraint",)),
    ]
    preds = [
        pred(("stab", "stabf"), "STO-A07", disposition="target_leakage"),
        pred(("p1", "p2", "p3", "p4"), "STO-A01", disposition="structural_constraint"),
        pred(("ambient", "inlet"), "STO-A01", disposition="structural_constraint"),
    ]
    metrics = score_predictions(preds, golds, dataset_id="d")
    assert metrics.detection.tp == 2
    assert metrics.detection.fp == 1
    assert metrics.detection.fn == 0
    assert metrics.detection.f1 == pytest.approx(0.8)


def test_score_predictions_empty_gold() -> None:
    metrics = score_predictions([pred(("a",), "STO-S02")], [], dataset_id="d")
    assert metrics.detection.fp == 1  # a prediction with no gold is a false positive


def test_optional_gold_not_penalized() -> None:
    golds = [gold(("v",), ("STO-S02",), optional=True)]
    metrics = score_predictions([], golds)
    assert metrics.detection.fn == 0  # unmatched optional gold is not a false negative


def test_disposition_mismatch_costs_at_disposition_level() -> None:
    golds = [gold(("a", "b"), ("STO-A01",), ("structural_constraint",))]
    preds = [pred(("a", "b"), "STO-A01", disposition="target_leakage")]
    metrics = score_predictions(preds, golds)
    assert metrics.detection.f1 == pytest.approx(1.0)  # detection matches
    assert metrics.disposition_aware.tp == 0  # disposition does not
    assert metrics.disposition_aware.fp == 1
    assert metrics.disposition_aware.fn == 1


def test_evaluate_split_aggregates_and_coverage() -> None:
    golds = {
        "d1": [gold(("a",), ("STO-S02",)), gold(ROWS, ("STO-R02",), gold_type="adjudicated")],
    }
    preds = [pred(("a",), "STO-S02", disposition="not_applicable"), pred(("q",), "STO-X00")]
    table = evaluate([_result("d1", preds)], golds, split="public-dev")
    mapping = table.to_mapping()
    assert mapping["detection"]["micro"]["tp"] == 1
    assert mapping["coverage"]["abstain_other"] == 1  # STO-X00 overlaps no unmatched gold
    assert mapping["coverage"]["objective_gold_recall"] == pytest.approx(1.0)
    assert mapping["coverage"]["adjudicated_gold_recall"] == pytest.approx(0.0)
    assert table.split == "public-dev"


def test_evaluate_abstain_hit() -> None:
    golds = {"d1": [gold(("a", "b"), ("STO-A01",))]}
    preds = [pred(("a", "b"), "STO-X00")]  # abstains on the exact gold support
    table = evaluate([_result("d1", preds)], golds, split="s")
    assert table.coverage.abstain_hit == 1
    assert table.coverage.abstain_other == 0


def test_evaluate_excludes_errors_and_missing_gold() -> None:
    error = _result("d2", [], error=ErrorRecord("resource", "timeout"))
    no_gold = _result("d3", [pred(("a",), "STO-S02")])
    table = evaluate([error, no_gold], {"d1": [gold(("a",), ("STO-S02",))]}, split="s")
    assert table.per_dataset == ()  # neither dataset is scored
    assert table.detection.micro.tp == 0


def test_evaluate_macro_over_two_datasets() -> None:
    golds = {
        "d1": [gold(("a",), ("STO-S02",))],
        "d2": [gold(("b",), ("STO-S03",))],
    }
    results = [
        _result("d1", [pred(("a",), "STO-S02")]),
        _result("d2", []),  # misses its gold entirely
    ]
    table = evaluate(results, golds, split="s")
    assert table.detection.macro_dataset_f1 == pytest.approx(0.5)  # (1.0 + 0.0) / 2
    assert set(table.per_class) == {"STO-S02", "STO-S03"}


def test_evaluate_all_excluded_is_empty_table() -> None:
    table = evaluate([_result("d", [], error=ErrorRecord("runtime", "x"))], {}, split="s")
    assert table.detection.micro.f1 == 0.0
    assert table.per_class == {}
    validate_metrics(table)  # an empty table is still schema-valid


def test_validate_gold_ok() -> None:
    validate_gold([gold(("a",), ("STO-S02",))])  # does not raise


def test_validate_gold_reserved_class() -> None:
    bad = gold(("a",), ("STO-X00",))
    with pytest.raises(InvalidGoldError, match="reserved"):
        validate_gold([bad])


def test_validate_gold_unknown_class() -> None:
    with pytest.raises(InvalidGoldError, match="unknown"):
        validate_gold([gold(("a",), ("STO-Z99",))])


def test_evaluate_without_validation_skips_gold_check() -> None:
    # validate=False bypasses the gold check, so an unknown class does not raise here
    table = evaluate(
        [_result("d1", [pred(("a",), "STO-S02")])],
        {"d1": [gold(("a",), ("STO-S02",))]},
        split="s",
        validate=False,
    )
    assert table.detection.micro.tp == 1


def test_validate_metrics_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    from synthaudit_bench.schemas.errors import SchemaValidationError

    def _boom(name: str, instance: Any, version: str | None = None) -> None:
        raise SchemaValidationError(schema_id="metrics", pointer="/", value="x", explanation="no")

    monkeypatch.setattr("synthaudit_bench.gold.scoring.schemas.validate_instance", _boom)
    table = scoring._build_table("s", [])
    with pytest.raises(MetricsError, match="failed schema validation"):
        validate_metrics(table)


def test_detector_summary() -> None:
    table = evaluate(
        [_result("d1", [pred(("a",), "STO-S02")])],
        {"d1": [gold(("a",), ("STO-S02",))]},
        split="public-dev",
    )
    summary = detector_summary(DetectorInfo("synthaudit", "0.1.0"), table)
    mapping = summary.to_mapping()
    assert mapping["detector"] == "synthaudit"
    assert mapping["detection_micro_f1"] == pytest.approx(1.0)
