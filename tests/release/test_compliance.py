"""Unit tests for the compliance suite (CS-1..CS-7)."""

from __future__ import annotations

import pandas as pd

from synthaudit_bench.compliance import ComplianceRecord, run_compliance
from synthaudit_bench.detector import (
    BaseDetector,
    DetectorCapabilities,
    ExecutionContext,
    RawFinding,
)
from synthaudit_bench.detector.adapters import StructuralBaselineDetector
from synthaudit_bench.model.dataset import DatasetObject
from synthaudit_bench.model.ontology import Disposition, GoldType
from synthaudit_bench.model.tuples import ROWS, GoldTuple


def _dataset() -> DatasetObject:
    table = pd.DataFrame(
        {
            "k": ["1"] * 250,
            "b": [str(i % 4) for i in range(250)],
            "c": [str(i % 4) for i in range(250)],
            "g": [str(i % 2) for i in range(250)],
        }
    )
    return DatasetObject(name="d1", table=table, target="g")


def _gold(
    classes: str = "STO-S02",
    *,
    gold_type: str = "objective",
    support: tuple[str, ...] | str = ("k",),
) -> GoldTuple:
    return GoldTuple(
        support=frozenset(support) if not isinstance(support, str) else support,
        classes=frozenset({classes}),
        dispositions=frozenset({Disposition.NOT_APPLICABLE}),
        gold_type=GoldType(gold_type),
        evidence="e",
    )


def test_baseline_passes_full_suite() -> None:
    gold = {
        "d1": [
            _gold("STO-S02", support=("k",)),
            _gold("STO-A08", support=("b", "c")),
            _gold("STO-S01", support=ROWS),
        ]
    }
    record = run_compliance(StructuralBaselineDetector(), [_dataset()], gold)
    assert isinstance(record, ComplianceRecord)
    assert record.passed is True
    assert {r.check for r in record.results} == {f"CS-{i}" for i in range(1, 8)}
    assert record.result_hash()


class _NullDetector(BaseDetector):
    def capabilities(self) -> DetectorCapabilities:
        return DetectorCapabilities(name="null", version="1.0.0")

    def detect(self, dataset: DatasetObject, context: ExecutionContext) -> list[RawFinding]:
        return []


def test_cs3_fails_when_objective_gold_missed() -> None:
    record = run_compliance(_NullDetector(), [_dataset()], {"d1": [_gold("STO-S02")]})
    cs3 = next(r for r in record.results if r.check == "CS-3")
    assert cs3.passed is False
    assert record.passed is False


def test_cs4_fails_on_adjudicated_miss() -> None:
    gold = {"d1": [_gold("STO-P01", gold_type="adjudicated", support=("b",))]}
    record = run_compliance(_NullDetector(), [_dataset()], gold)
    cs4 = next(r for r in record.results if r.check == "CS-4")
    assert cs4.passed is False


def test_cs1_fails_on_unknown_gold_class() -> None:
    record = run_compliance(StructuralBaselineDetector(), [_dataset()], {"d1": [_gold("STO-Z99")]})
    cs1 = next(r for r in record.results if r.check == "CS-1")
    assert cs1.passed is False
    assert "validation failed" in cs1.detail


def test_cs7_cross_check_passes_with_reference() -> None:
    gold = {"d1": [_gold("STO-S02")]}
    record = run_compliance(
        StructuralBaselineDetector(), [_dataset()], gold, expected_outputs={"d1": ["STO-S02"]}
    )
    cs7 = next(r for r in record.results if r.check == "CS-7")
    assert cs7.passed is True
    assert "reproduce" in cs7.detail


def test_pool_ignores_absent_class() -> None:
    from synthaudit_bench.compliance import _pool

    assert _pool({}, ["STO-A01"]) == (0, 0, 0)


def test_record_to_mapping() -> None:
    record = run_compliance(StructuralBaselineDetector(), [_dataset()], {"d1": [_gold("STO-S02")]})
    mapping = record.to_mapping()
    assert mapping["implementation"] == "structural-baseline"
    assert len(mapping["results"]) == 7
