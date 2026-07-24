"""Unit tests for the built-in structural baseline detector."""

from __future__ import annotations

import pandas as pd

from synthaudit_bench.detector import ExecutionContext, run_detector
from synthaudit_bench.detector.adapters import StructuralBaselineDetector, builtin_registry
from synthaudit_bench.model.dataset import DatasetObject
from synthaudit_bench.model.tuples import ROWS


def _dataset(table: pd.DataFrame, target: str | None = None) -> DatasetObject:
    return DatasetObject(name="d", table=table, target=target)


def test_detects_constant_duplicate_and_rows() -> None:
    base = pd.DataFrame(
        {
            "k": ["1"] * 20,
            "b": [str(i % 4) for i in range(20)],
            "c": [str(i % 4) for i in range(20)],
            "g": [str(i % 2) for i in range(20)],
        }
    )
    detector = StructuralBaselineDetector()
    findings = list(detector.detect(_dataset(base), ExecutionContext()))
    classes = {f.identifier for f in findings}
    assert "STO-S02" in classes  # constant k
    assert "STO-A08" in classes  # b == c
    assert "STO-S01" in classes  # many duplicate rows
    row_finding = next(f for f in findings if f.identifier == "STO-S01")
    assert row_finding.support == ROWS


def test_no_structure_yields_nothing() -> None:
    clean = pd.DataFrame({"a": [str(i) for i in range(10)], "b": [str(i * 2) for i in range(10)]})
    findings = list(StructuralBaselineDetector().detect(_dataset(clean), ExecutionContext()))
    assert findings == []


def test_empty_table_skips_row_check() -> None:
    empty = pd.DataFrame({"a": pd.Series(dtype=str), "b": pd.Series(dtype=str)})
    findings = list(StructuralBaselineDetector().detect(_dataset(empty), ExecutionContext()))
    # entirely-missing columns yield S02 (and equal empty columns A08); no rows -> no S01
    assert all(f.identifier != "STO-S01" for f in findings)


def test_runs_through_run_detector() -> None:
    base = pd.DataFrame(
        {
            "k": ["1"] * 250,
            "b": [str(i) for i in range(250)],
            "c": [str(i) for i in range(250)],
            "g": ["A"] * 250,
        }
    )
    result = run_detector(StructuralBaselineDetector(), _dataset(base, "g"), ExecutionContext())
    assert result.error is None
    assert any(t.sto_class == "STO-S02" for t in result.tuples)


def test_capabilities_and_builtin_registry() -> None:
    caps = StructuralBaselineDetector().capabilities()
    assert caps.name == "structural-baseline"
    registry = builtin_registry()
    assert registry.contains("structural-baseline")
    assert registry.create("structural-baseline").capabilities().name == "structural-baseline"
