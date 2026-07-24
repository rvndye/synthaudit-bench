"""A minimal, reference-free structural baseline detector (pandas only).

This baseline detects the objective structural classes that are exactly
determinable from the released table without a learned probe: constant columns
(STO-S02), duplicate or near-copy columns (STO-A08, exact string equality), and
duplicate rows (STO-S01). It is deterministic, operates on the full non-missing
data, reads only the immutable dataset, and never imports the reference
implementation. Its purpose is to prove the task is non-trivial and to make the
benchmark runnable end-to-end (architecture ``detector.adapters.baselines``); it is
not the reference detector.
"""

from __future__ import annotations

from collections.abc import Iterable

from synthaudit_bench.detector.base import (
    BaseDetector,
    DetectorCapabilities,
    ExecutionContext,
    RawFinding,
)
from synthaudit_bench.detector.registry import DetectorRegistry, register_detector
from synthaudit_bench.model.dataset import DatasetObject
from synthaudit_bench.model.tuples import ROWS

__all__ = ["StructuralBaselineDetector", "builtin_registry"]

_TAU_DUPROW = 0.01


class StructuralBaselineDetector(BaseDetector):
    """A pandas-only detector for the exactly-determinable objective classes."""

    def capabilities(self) -> DetectorCapabilities:
        """Declare support for the objective S and A classes it can determine."""
        return DetectorCapabilities(
            name="structural-baseline",
            version="1.0.0",
            implementation="synthaudit-bench-baseline",
            required_bench_version="1.0.0",
            sto_categories=frozenset({"STO-S02", "STO-A08", "STO-S01"}),
        )

    def detect(self, dataset: DatasetObject, context: ExecutionContext) -> Iterable[RawFinding]:
        """Emit constant-column, duplicate-column, and duplicate-row findings."""
        table = dataset.table
        columns = list(dataset.columns)

        for column in columns:
            if table[column].nunique(dropna=True) <= 1:
                yield RawFinding("STO-S02", (column,), evidence={"cardinality": 1})

        for i, left in enumerate(columns):
            for right in columns[i + 1 :]:
                if table[left].astype(str).equals(table[right].astype(str)):
                    yield RawFinding("STO-A08", (left, right), evidence={"equal": True})

        n_rows = int(table.shape[0])
        if n_rows:
            duplicate_fraction = int(table.duplicated().sum()) / n_rows
            if duplicate_fraction > _TAU_DUPROW:
                yield RawFinding(
                    "STO-S01", ROWS, evidence={"duplicate_row_fraction": duplicate_fraction}
                )


def builtin_registry() -> DetectorRegistry:
    """Return a registry containing the built-in baseline detector."""
    return register_detector("structural-baseline", StructuralBaselineDetector)
