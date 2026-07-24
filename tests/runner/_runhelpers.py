"""Helpers for runner tests: datasets with distinct content and example detectors."""

from __future__ import annotations

from typing import Any

import pandas as pd

from synthaudit_bench.detector import (
    BaseDetector,
    DetectorCapabilities,
    ExecutionContext,
    RawFinding,
    build_ontology_mapper,
)
from synthaudit_bench.model.dataset import DatasetObject


def make_dataset(name: str, *, rows: int = 250) -> DatasetObject:
    """A 4-column, above-minimum dataset whose content is distinct per ``name``."""
    table = pd.DataFrame(
        {
            "k": [name] * rows,  # constant column (distinct content per dataset)
            "b": [str(i) for i in range(rows)],
            "c": [str(i) for i in range(rows)],
            "grade": ["A" if i % 2 else "B" for i in range(rows)],
        }
    )
    return DatasetObject(name=name, table=table, target="grade")


def mapper() -> Any:
    return build_ontology_mapper({"STO-S02": "STO-S02"})


class ConstDetector(BaseDetector):
    """Flags constant columns as STO-S02."""

    def capabilities(self) -> DetectorCapabilities:
        return DetectorCapabilities(name="const", version="1.0.0", sto_categories=frozenset({"S"}))

    def detect(self, dataset: DatasetObject, context: ExecutionContext) -> list[RawFinding]:
        return [
            RawFinding("STO-S02", (column,))
            for column in dataset.columns
            if dataset.table[column].nunique(dropna=True) <= 1
        ]


class ErrorDetector(BaseDetector):
    """Always raises, to exercise per-dataset isolation."""

    def capabilities(self) -> DetectorCapabilities:
        return DetectorCapabilities(name="boom", version="1.0.0")

    def detect(self, dataset: DatasetObject, context: ExecutionContext) -> list[RawFinding]:
        raise RuntimeError("detector failed")
