"""Release-candidate regression tests for runner hardening (MAJ-1, MIN-6, MIN-4).

MAJ-1: a detector whose ``capabilities()`` raises must not terminate the batch; the
run completes with a per-dataset structured ``init`` failure and a fallback identity.
MIN-6: the thresholds mapping injected into the execution context is immutable and
decoupled from the caller's dict. MIN-4: a duplicate dataset id is a planning error.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

import pytest
from _runhelpers import make_dataset

from synthaudit_bench.detector import (
    BaseDetector,
    DetectionResult,
    DetectorCapabilities,
    ExecutionContext,
)
from synthaudit_bench.model.dataset import DatasetObject
from synthaudit_bench.runner.engine import run_benchmark
from synthaudit_bench.runner.errors import RunnerError
from synthaudit_bench.runner.plan import plan_run


class _CapabilitiesBoom(BaseDetector):
    """A detector whose capability discovery raises (MAJ-1)."""

    def capabilities(self) -> DetectorCapabilities:
        raise RuntimeError("capabilities exploded")

    def detect(self, dataset: DatasetObject, context: ExecutionContext) -> DetectionResult:
        raise AssertionError("detect must not be reached when capabilities() fails")


class _ThresholdRecorder(BaseDetector):
    """Records the thresholds mapping it receives from the context (MIN-6)."""

    def __init__(self) -> None:
        self.seen: Mapping[str, Any] | None = None

    def capabilities(self) -> DetectorCapabilities:
        return DetectorCapabilities(name="rec", version="1.0.0")

    def detect(self, dataset: DatasetObject, context: ExecutionContext) -> DetectionResult:
        self.seen = context.thresholds
        return DetectionResult(findings=())


def test_capabilities_failure_does_not_terminate_run() -> None:
    datasets = [make_dataset("d1"), make_dataset("d2")]
    outcome = run_benchmark(datasets, _CapabilitiesBoom(), split="public-dev")
    # Fail-open: every dataset produces a structured init error and the batch completes.
    assert [r.dataset_id for r in outcome.results] == ["d1", "d2"]
    assert all(r.error is not None and r.error.code == "init" for r in outcome.results)
    # The fallback identity is built from the detector type name.
    assert outcome.results[0].detector.name == "_CapabilitiesBoom"
    assert outcome.results[0].detector.version == "unknown"
    # The run log records the initialization failure once, at the supervisor boundary.
    assert any(event.kind == "detector_init_error" for event in outcome.events)


def test_capabilities_failure_still_yields_valid_manifest() -> None:
    outcome = run_benchmark([make_dataset("d1")], _CapabilitiesBoom(), split="public-dev")
    # The manifest is still assembled and schema-validated (validate=True by default).
    assert outcome.manifest.split == "public-dev"
    assert outcome.manifest.datasets[0].status == "init"


@pytest.mark.parametrize("thresholds", [None, {"operating_point": 0.5}])
def test_thresholds_are_immutable_in_context(thresholds: dict[str, float] | None) -> None:
    detector = _ThresholdRecorder()
    run_benchmark([make_dataset("d1")], detector, split="public-dev", thresholds=thresholds)
    # A read-only proxy is handed to the detector on both the None and the dict path.
    assert isinstance(detector.seen, MappingProxyType)


def test_thresholds_dict_is_copied_not_aliased() -> None:
    detector = _ThresholdRecorder()
    source = {"operating_point": 0.5}
    run_benchmark([make_dataset("d1")], detector, split="public-dev", thresholds=source)
    source["operating_point"] = 0.9  # mutating the caller's dict must not leak into the run
    assert detector.seen is not None
    assert dict(detector.seen) == {"operating_point": 0.5}


def test_plan_run_rejects_duplicate_ids() -> None:
    with pytest.raises(RunnerError, match="duplicate dataset id"):
        plan_run([make_dataset("dup"), make_dataset("dup")])


def test_run_benchmark_rejects_duplicate_ids() -> None:
    with pytest.raises(RunnerError, match="duplicate dataset id"):
        run_benchmark(
            [make_dataset("dup"), make_dataset("dup")], _ThresholdRecorder(), split="public-dev"
        )
