"""Shared helpers for the detector-subsystem tests: datasets and example detectors."""

from __future__ import annotations

from collections.abc import Callable
from types import MappingProxyType
from typing import Any

import pandas as pd

from synthaudit_bench.detector import (
    BaseDetector,
    DetectorCapabilities,
    ExecutionContext,
    RawFinding,
)
from synthaudit_bench.model.dataset import DatasetObject
from synthaudit_bench.model.enums import (
    FrameStratum,
    GeneratorFamily,
    ProvenanceConfidence,
    Task,
)
from synthaudit_bench.model.records import (
    DatasetRecord,
    License,
    Loader,
    Source,
    Transparency,
)

DetectFn = Callable[[DatasetObject, ExecutionContext], Any]


def make_record(
    dsid: str = "ds-x", *, target: str | None = "grade", modality: str = "tabular"
) -> DatasetRecord:
    return DatasetRecord(
        id=dsid,
        title="T",
        frame_stratum=FrameStratum.PLANTED,
        domain="energy",
        generator_family=GeneratorFamily.RULE_BASED,
        provenance_confidence=ProvenanceConfidence.DOCUMENTED,
        task=Task.CLASSIFICATION,
        target=target,
        license=License("CC0", redistribute=True, fetch_scriptable=True),
        source=Source(("u",), MappingProxyType({"f.csv": "a" * 64}), "2026-07-23"),
        loader=Loader("csv"),
        transparency=Transparency(True, True, True, True),
        citation="c",
        modality=modality,
    )


def make_dataset(
    rows: int = 250,
    *,
    target: str | None = "grade",
    modality: str = "tabular",
    with_record: bool = True,
) -> DatasetObject:
    """A 4-column dataset: a constant column, two identical columns, and a label."""
    data = {
        "const": ["1"] * rows,
        "b": [str(i) for i in range(rows)],
        "c": [str(i) for i in range(rows)],
        "grade": ["A" if i % 2 else "B" for i in range(rows)],
    }
    record = make_record(target=target if target is not None else "grade", modality=modality)
    return DatasetObject(
        name="ds-x",
        table=pd.DataFrame(data),
        target=target,
        record=record if with_record else None,
    )


def caps(**overrides: Any) -> DetectorCapabilities:
    fields: dict[str, Any] = {"name": "test", "version": "0.1.0"}
    fields.update(overrides)
    return DetectorCapabilities(**fields)


class FunctionDetector(BaseDetector):
    """A BaseDetector whose behavior is supplied as callables (has lifecycle hooks)."""

    def __init__(
        self,
        capabilities: DetectorCapabilities,
        detect: DetectFn,
        *,
        setup: Callable[[ExecutionContext], None] | None = None,
        teardown: Callable[[], None] | None = None,
    ) -> None:
        self._caps = capabilities
        self._detect = detect
        self._setup = setup
        self._teardown = teardown

    def capabilities(self) -> DetectorCapabilities:
        return self._caps

    def detect(self, dataset: DatasetObject, context: ExecutionContext) -> Any:
        return self._detect(dataset, context)

    def setup(self, context: ExecutionContext) -> None:
        if self._setup is not None:
            self._setup(context)

    def teardown(self) -> None:
        if self._teardown is not None:
            self._teardown()


class MinimalDetector:
    """A detector that implements the protocol directly, with no lifecycle hooks."""

    def __init__(self, capabilities: DetectorCapabilities, detect: DetectFn) -> None:
        self._caps = capabilities
        self._detect = detect

    def capabilities(self) -> DetectorCapabilities:
        return self._caps

    def detect(self, dataset: DatasetObject, context: ExecutionContext) -> Any:
        return self._detect(dataset, context)


def const_findings(dataset: DatasetObject, context: ExecutionContext) -> list[RawFinding]:
    """Emit an STO-S02 finding for each constant column and an A08 for the b/c pair."""
    findings = [
        RawFinding(identifier="STO-S02", support=(col,))
        for col in dataset.columns
        if dataset.table[col].nunique() == 1
    ]
    findings.append(RawFinding(identifier="STO-A08", support=("b", "c")))
    return findings
