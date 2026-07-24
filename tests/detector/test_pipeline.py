"""End-to-end detector-pipeline tests: a minimal plugin, discovery, run, determinism."""

from __future__ import annotations

from collections.abc import Iterable

import pytest
from _dethelpers import make_dataset

from synthaudit_bench.detector import (
    BaseDetector,
    DetectorCapabilities,
    DetectorRegistry,
    ExecutionContext,
    OntologyMapper,
    RawFinding,
    build_ontology_mapper,
    detector_metadata,
    discover_detectors,
    register_detector,
    run_detector,
)
from synthaudit_bench.model.dataset import DatasetObject
from synthaudit_bench.model.ontology import Disposition

pytestmark = pytest.mark.integration


class ConstantColumnDetector(BaseDetector):
    """A minimal, reference-free detector: flags constant columns (STO-S02).

    This is the smallest useful implementation of the public protocol; it depends
    only on the documented interface and the immutable dataset, never on benchmark
    internals.
    """

    def capabilities(self) -> DetectorCapabilities:
        return DetectorCapabilities(
            name="constant-column",
            version="1.0.0",
            implementation="example",
            required_bench_version="1.0.0",
            sto_categories=frozenset({"S"}),
        )

    def detect(self, dataset: DatasetObject, context: ExecutionContext) -> Iterable[RawFinding]:
        for column in dataset.columns:
            if dataset.table[column].nunique(dropna=True) <= 1:
                yield RawFinding(
                    identifier="constant",
                    support=(column,),
                    severity="low",
                    evidence={"cardinality": 1},
                )


def _mapper() -> OntologyMapper:
    return build_ontology_mapper({"constant": "STO-S02"})


class _EP:
    name = "constant-column"

    def load(self) -> type[ConstantColumnDetector]:
        return ConstantColumnDetector


def test_register_discover_and_run_minimal_plugin() -> None:
    registry = discover_detectors(entry_points_override=[_EP()])
    assert isinstance(registry, DetectorRegistry)
    assert registry.names() == ("constant-column",)

    detector = registry.create("constant-column")
    meta = detector_metadata(detector)
    assert meta.implementation == "example"
    assert meta.reference_free is True

    result = run_detector(detector, make_dataset(), ExecutionContext(), mapper=_mapper())
    assert result.error is None
    assert len(result.tuples) == 1
    tuple_ = result.tuples[0]
    assert tuple_.sto_class == "STO-S02"
    assert tuple_.support == frozenset({"const"})
    assert tuple_.disposition is Disposition.NOT_APPLICABLE
    assert tuple_.severity is not None and tuple_.severity.value == "low"


def test_pipeline_is_deterministic() -> None:
    detector = ConstantColumnDetector()
    dataset = make_dataset()
    context = ExecutionContext(seed=42)
    first = run_detector(detector, dataset, context, mapper=_mapper())
    second = run_detector(detector, dataset, context, mapper=_mapper())
    assert first.content_hash() == second.content_hash()  # identity excludes timing
    assert first.tuples == second.tuples


def test_programmatic_registration_round_trip() -> None:
    registry = register_detector("constant-column", ConstantColumnDetector)
    detector = registry.create("constant-column")
    result = run_detector(detector, make_dataset(), ExecutionContext(), mapper=_mapper())
    assert result.detector.name == "constant-column"
    assert result.dataset_sha256 == make_dataset().content_hash()
