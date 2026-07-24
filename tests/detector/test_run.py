"""Unit tests for isolated detector execution and capability validation."""

from __future__ import annotations

import threading
from typing import Any

import pytest
from _dethelpers import (
    FunctionDetector,
    MinimalDetector,
    caps,
    const_findings,
    make_dataset,
)

from synthaudit_bench.detector import (
    DetectionResult,
    ExecutionContext,
    RawFinding,
    run_detector,
    validate_detector,
)
from synthaudit_bench.detector.errors import (
    UnsupportedCapabilityError,
    UnsupportedVersionError,
)


def _noop(dataset: Any, context: Any) -> list[RawFinding]:
    return []


# --------------------------------------------------------------------------- #
# validate_detector                                                           #
# --------------------------------------------------------------------------- #


def test_validate_ok_without_dataset() -> None:
    validate_detector(FunctionDetector(caps(), _noop), ExecutionContext())  # does not raise


def test_validate_ok_with_dataset_and_types() -> None:
    detector = FunctionDetector(caps(logical_types=frozenset({"numeric", "categorical"})), _noop)
    validate_detector(detector, ExecutionContext(), dataset=make_dataset())  # does not raise


def test_validate_ok_with_dataset_open_types() -> None:
    # empty logical_types -> the type-inference branch is skipped
    validate_detector(FunctionDetector(caps(), _noop), ExecutionContext(), dataset=make_dataset())


def test_validate_version_raises() -> None:
    detector = FunctionDetector(caps(required_bench_version="2.0.0"), _noop)
    with pytest.raises(UnsupportedVersionError):
        validate_detector(detector, ExecutionContext())


def test_validate_modality_raises() -> None:
    detector = FunctionDetector(caps(modalities=frozenset({"image"})), _noop)
    with pytest.raises(UnsupportedCapabilityError):
        validate_detector(detector, ExecutionContext(), dataset=make_dataset())


# --------------------------------------------------------------------------- #
# run_detector: success and lifecycle                                         #
# --------------------------------------------------------------------------- #


def test_run_success() -> None:
    result = run_detector(
        FunctionDetector(caps(), const_findings), make_dataset(), ExecutionContext()
    )
    assert result.error is None
    assert result.dataset_id == "ds-x"
    assert [t.sto_class for t in result.tuples] == ["STO-A08", "STO-S02"]


def test_run_minimal_detector_without_lifecycle() -> None:
    result = run_detector(
        MinimalDetector(caps(), const_findings), make_dataset(), ExecutionContext()
    )
    assert result.error is None
    assert len(result.tuples) == 2


def test_run_teardown_failure_is_swallowed() -> None:
    def boom() -> None:
        raise RuntimeError("teardown blew up")

    detector = FunctionDetector(
        caps(), lambda d, c: [RawFinding("STO-S02", ("const",))], teardown=boom
    )
    result = run_detector(detector, make_dataset(), ExecutionContext())
    assert result.error is None
    assert len(result.tuples) == 1


def test_run_no_record_dataset_defaults_modality() -> None:
    result = run_detector(
        FunctionDetector(caps(), const_findings),
        make_dataset(with_record=False),
        ExecutionContext(),
    )
    assert result.error is None


# --------------------------------------------------------------------------- #
# run_detector: isolation and failures                                        #
# --------------------------------------------------------------------------- #


def test_run_capabilities_failure_is_init_error() -> None:
    class BadCaps:
        def capabilities(self) -> Any:
            raise RuntimeError("no caps")

        def detect(self, dataset: Any, context: Any) -> Any:
            return []

    result = run_detector(BadCaps(), make_dataset(), ExecutionContext())
    assert result.error is not None and result.error.code == "init"
    assert result.detector.name == "BadCaps"


def test_run_setup_failure_is_init_error() -> None:
    def boom_setup(context: Any) -> None:
        raise RuntimeError("setup fail")

    detector = FunctionDetector(caps(), _noop, setup=boom_setup)
    result = run_detector(detector, make_dataset(), ExecutionContext())
    assert result.error is not None and result.error.code == "init"


def test_run_detector_exception_is_runtime() -> None:
    def boom(dataset: Any, context: Any) -> Any:
        raise ValueError("detector broke")

    result = run_detector(FunctionDetector(caps(), boom), make_dataset(), ExecutionContext())
    assert result.error is not None and result.error.code == "runtime"
    assert "detector broke" in result.error.detail


def test_run_mutation_is_runtime() -> None:
    def mutate(dataset: Any, context: Any) -> Any:
        dataset.table.iloc[0, 0] = "zzz"
        return []

    result = run_detector(FunctionDetector(caps(), mutate), make_dataset(), ExecutionContext())
    assert result.error is not None and result.error.code == "runtime"
    assert "mutated" in result.error.detail


def test_run_normalization_failure() -> None:
    detector = FunctionDetector(caps(), lambda d, c: [RawFinding("STO-S02", "not-a-token")])
    result = run_detector(detector, make_dataset(), ExecutionContext())
    assert result.error is not None and result.error.code == "invalid_findings"


def test_run_version_capability_error() -> None:
    detector = FunctionDetector(caps(required_bench_version="2.0.0"), const_findings)
    result = run_detector(detector, make_dataset(), ExecutionContext())
    assert result.error is not None and result.error.code == "unsupported_version"


def test_run_modality_capability_error() -> None:
    detector = FunctionDetector(caps(modalities=frozenset({"image"})), const_findings)
    result = run_detector(detector, make_dataset(), ExecutionContext())
    assert result.error is not None and result.error.code == "unsupported_capability"


def test_run_logical_type_capability_error() -> None:
    detector = FunctionDetector(caps(logical_types=frozenset({"numeric"})), const_findings)
    result = run_detector(detector, make_dataset(), ExecutionContext())
    assert result.error is not None and result.error.code == "unsupported_capability"


# --------------------------------------------------------------------------- #
# run_detector: below-minimum, partial, timeout                               #
# --------------------------------------------------------------------------- #


def test_run_below_minimum_emits_note() -> None:
    result = run_detector(
        FunctionDetector(caps(), const_findings), make_dataset(rows=10), ExecutionContext()
    )
    assert result.notes == ("below_minimum",)
    assert result.tuples == ()


def test_run_honor_minimum_false_runs_detector() -> None:
    result = run_detector(
        FunctionDetector(caps(), _noop),
        make_dataset(rows=10),
        ExecutionContext(),
        honor_minimum=False,
    )
    assert result.notes == ()
    assert result.error is None


def test_run_partial_and_notes() -> None:
    def detect(dataset: Any, context: Any) -> DetectionResult:
        return DetectionResult(
            findings=(RawFinding("STO-S02", ("const",)),), notes=("scanned",), partial=True
        )

    result = run_detector(FunctionDetector(caps(), detect), make_dataset(), ExecutionContext())
    assert "scanned" in result.notes
    assert "partial:true" in result.notes


def test_run_within_timeout_completes() -> None:
    detector = FunctionDetector(caps(), lambda d, c: [RawFinding("STO-S02", ("const",))])
    result = run_detector(detector, make_dataset(), ExecutionContext(timeout_s=5.0))
    assert result.error is None
    assert len(result.tuples) == 1


def test_run_timeout_is_resource_error() -> None:
    release = threading.Event()

    def slow(dataset: Any, context: Any) -> Any:
        release.wait(timeout=5.0)
        return []

    detector = FunctionDetector(caps(), slow)
    result = run_detector(detector, make_dataset(), ExecutionContext(timeout_s=0.05))
    release.set()  # let the abandoned worker finish promptly
    assert result.error is not None and result.error.code == "resource"
