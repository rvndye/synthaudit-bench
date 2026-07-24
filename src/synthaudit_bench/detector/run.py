"""Isolated, deterministic execution of one detector on one dataset.

:func:`run_detector` is the task boundary (architecture ``task``): it validates
capabilities, honors the below-minimum rule, runs the detector under an optional
wall-clock budget, verifies the detector did not mutate the immutable dataset, and
normalizes the raw findings into an :class:`~synthaudit_bench.model.results.AuditResult`.
It never raises: every failure, whether a capability mismatch, a timeout, a
detector exception, or a malformed finding, becomes a structured
:class:`~synthaudit_bench.model.results.ErrorRecord` on the result, so one
detector's failure is isolated and never terminates a batch (specification
Section 5.9). :func:`validate_detector` is the raising pre-flight check for
callers that want capability validation on its own.
"""

from __future__ import annotations

import contextlib
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout

from synthaudit_bench.detector.base import (
    DetectionResult,
    Detector,
    DetectorCapabilities,
    ExecutionContext,
    capability_issues,
)
from synthaudit_bench.detector.errors import (
    DetectorInitError,
    DetectorTimeoutError,
    NormalizationError,
    UnsupportedCapabilityError,
    UnsupportedVersionError,
)
from synthaudit_bench.detector.normalize import normalize_findings
from synthaudit_bench.detector.ontology_map import OntologyMapper
from synthaudit_bench.load import below_minimum, infer_column_types
from synthaudit_bench.model.dataset import DatasetObject
from synthaudit_bench.model.results import AuditResult, DetectorInfo, ErrorRecord

__all__ = ["run_detector", "validate_detector"]


def _detector_info(caps: DetectorCapabilities) -> DetectorInfo:
    return DetectorInfo(
        name=caps.name,
        version=caps.version,
        reference_free=caps.reference_free,
        capabilities=tuple(sorted(caps.sto_categories)),
        probe_family=caps.probe_family,
    )


def _dataset_modality(dataset: DatasetObject) -> str:
    return dataset.record.modality if dataset.record is not None else "tabular"


def _dataset_logical_types(dataset: DatasetObject) -> frozenset[str]:
    return frozenset(str(value) for value in infer_column_types(dataset.table).values())


def _safe_teardown(detector: Detector) -> None:
    teardown = getattr(detector, "teardown", None)
    if callable(teardown):
        # Graceful shutdown is best-effort; a teardown error never masks a result.
        with contextlib.suppress(Exception):
            teardown()


def _run_detect(
    detector: Detector, dataset: DatasetObject, context: ExecutionContext
) -> DetectionResult:
    setup = getattr(detector, "setup", None)
    if callable(setup):
        try:
            setup(context)
        except Exception as exc:
            raise DetectorInitError(f"detector setup failed: {exc}") from exc
    try:
        output = detector.detect(dataset, context)
        result = (
            output
            if isinstance(output, DetectionResult)
            else DetectionResult(findings=tuple(output))
        )
    except BaseException:
        _safe_teardown(detector)
        raise
    _safe_teardown(detector)
    return result


def _execute(
    detector: Detector,
    dataset: DatasetObject,
    context: ExecutionContext,
    timeout_s: float | None,
) -> DetectionResult:
    if timeout_s is None:
        return _run_detect(detector, dataset, context)
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(_run_detect, detector, dataset, context)
    try:
        result = future.result(timeout=timeout_s)
    except FuturesTimeout as exc:
        # Do not wait on the runaway worker; hard cancellation is the runner's
        # process-pool job. Here we detect and record the breach (E-4).
        executor.shutdown(wait=False, cancel_futures=True)
        raise DetectorTimeoutError(f"detector exceeded its {timeout_s}s budget") from exc
    executor.shutdown(wait=False)
    return result


def _error_result(
    dataset: DatasetObject,
    info: DetectorInfo,
    dataset_sha: str,
    code: str,
    detail: str,
) -> AuditResult:
    return AuditResult(
        dataset_id=dataset.name,
        dataset_sha256=dataset_sha,
        detector=info,
        tuples=(),
        error=ErrorRecord(code=code, detail=detail),
    )


def validate_detector(
    detector: Detector, context: ExecutionContext, *, dataset: DatasetObject | None = None
) -> None:
    """Validate ``detector`` against ``context`` (and ``dataset`` if given), raising.

    Checks benchmark and ontology version compatibility always, and the dataset's
    modality and logical types when a dataset is supplied. This is the explicit
    pre-flight gate; :func:`run_detector` performs the same check internally but
    records a structured error instead of raising.

    Raises:
        UnsupportedVersionError: if a required version is not satisfied.
        UnsupportedCapabilityError: if the modality or logical types are unsupported.
    """
    caps = detector.capabilities()
    modality: str | None = None
    logical_types: frozenset[str] | None = None
    if dataset is not None:
        modality = _dataset_modality(dataset)
        if caps.logical_types:
            logical_types = _dataset_logical_types(dataset)
    issues = capability_issues(caps, context, modality=modality, logical_types=logical_types)
    if issues:
        issue = issues[0]
        if issue.code == "unsupported_version":
            raise UnsupportedVersionError(issue.detail)
        raise UnsupportedCapabilityError(issue.detail)


def run_detector(
    detector: Detector,
    dataset: DatasetObject,
    context: ExecutionContext,
    *,
    mapper: OntologyMapper | None = None,
    honor_minimum: bool = True,
) -> AuditResult:
    """Run ``detector`` on ``dataset`` and return a normalized :class:`AuditResult`.

    The pipeline is: declare capabilities, validate them against the context and
    dataset, honor the below-minimum rule (empty findings plus a ``below_minimum``
    note, specification Section 5.9 E-2), execute the detector under
    ``context.timeout_s`` with per-dataset isolation, confirm the detector did not
    mutate the dataset, and normalize the findings. Any failure becomes a
    structured error on the result; this function never raises.
    """
    try:
        caps = detector.capabilities()
    except Exception as exc:
        info = DetectorInfo(name=type(detector).__name__, version="unknown")
        return _error_result(
            dataset, info, dataset.content_hash(), "init", f"capabilities() failed: {exc}"
        )

    info = _detector_info(caps)
    dataset_sha = dataset.content_hash()

    logical_types = _dataset_logical_types(dataset) if caps.logical_types else None
    issues = capability_issues(
        caps, context, modality=_dataset_modality(dataset), logical_types=logical_types
    )
    if issues:
        return _error_result(dataset, info, dataset_sha, issues[0].code, issues[0].detail)

    if honor_minimum and below_minimum(dataset.table):
        return AuditResult(dataset.name, dataset_sha, info, tuples=(), notes=("below_minimum",))

    try:
        detection = _execute(detector, dataset, context, context.timeout_s)
    except DetectorTimeoutError as exc:
        return _error_result(dataset, info, dataset_sha, "resource", str(exc))
    except DetectorInitError as exc:
        return _error_result(dataset, info, dataset_sha, "init", str(exc))
    except Exception as exc:  # isolation: any detector exception is a runtime failure
        return _error_result(dataset, info, dataset_sha, "runtime", f"detector raised: {exc}")

    if dataset.content_hash() != dataset_sha:
        return _error_result(dataset, info, dataset_sha, "runtime", "detector mutated the dataset")

    try:
        tuples = normalize_findings(
            detection.findings, dataset, mapper=mapper, sto_version=context.sto_version
        )
    except NormalizationError as exc:
        return _error_result(dataset, info, dataset_sha, exc.code, str(exc))

    notes = tuple(detection.notes)
    if detection.partial:
        notes = (*notes, "partial:true")
    return AuditResult(dataset.name, dataset_sha, info, tuples=tuples, notes=notes)
