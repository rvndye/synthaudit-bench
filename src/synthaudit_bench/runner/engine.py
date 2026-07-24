"""The batch execution engine (architecture Section 7).

``run_benchmark`` executes one detector over a set of datasets and assembles the
reproducibility :class:`~synthaudit_bench.model.manifest.RunManifest`. Datasets are
dispatched in a fixed sorted-by-id order and every result is ordered by dataset id,
so the outputs never depend on thread scheduling: serial and parallel runs of the
same inputs produce identical results and an identical manifest hash (which
excludes the injected timestamps). Execution is fail-open per dataset (a detector
failure is isolated into a structured result by
:func:`~synthaudit_bench.detector.run.run_detector`) and fail-closed on integrity
(a dataset whose content hash does not match its expected hash aborts the run).

Concurrency is optional and does not change semantics: each dataset's result is
computed independently and deterministically, and the shared cache and journal are
written from a single thread in dataset-id order after collection. No pure code
reads a clock; the run timestamps and environment are injected at this supervisor
boundary.
"""

from __future__ import annotations

import dataclasses
import json
import platform
import sys
from collections.abc import Callable, Iterable, Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from synthaudit_bench import schemas
from synthaudit_bench.detector import ExecutionContext, detector_capabilities, run_detector
from synthaudit_bench.detector.base import Detector
from synthaudit_bench.detector.ontology_map import OntologyMapper
from synthaudit_bench.model.config import ResourceLimits
from synthaudit_bench.model.manifest import DatasetEntry, Environment, RunManifest, Timestamps
from synthaudit_bench.model.results import AuditResult, DetectorInfo, ErrorRecord
from synthaudit_bench.runner.cache import NullCache, ResultCache, result_cache_key
from synthaudit_bench.runner.errors import IntegrityAbort
from synthaudit_bench.runner.journal import Journal
from synthaudit_bench.runner.plan import WorkItem, plan_run

__all__ = [
    "RunEvent",
    "RunOutcome",
    "capture_environment",
    "run_benchmark",
    "run_id",
    "write_artifacts",
]

_EPOCH = "1970-01-01T00:00:00Z"


@dataclass(frozen=True, slots=True)
class RunEvent:
    """One structured run event (no wall-clock; ordering is by emission)."""

    kind: str
    dataset_id: str | None = None
    status: str | None = None
    cached: bool = False

    def to_mapping(self) -> dict[str, Any]:
        """Return the primitive mapping for this event."""
        mapping: dict[str, Any] = {"kind": self.kind}
        if self.dataset_id is not None:
            mapping["dataset_id"] = self.dataset_id
        if self.status is not None:
            mapping["status"] = self.status
        if self.cached:
            mapping["cached"] = True
        return mapping


@dataclass(frozen=True, slots=True)
class RunOutcome:
    """The outcome of a run: ordered results, the manifest, and the event log."""

    run_id: str
    results: tuple[AuditResult, ...]
    manifest: RunManifest
    events: tuple[RunEvent, ...] = ()

    @property
    def scored(self) -> int:
        """The number of datasets that produced a result without an error."""
        return sum(1 for r in self.results if r.error is None)

    @property
    def failed(self) -> int:
        """The number of datasets recorded as a failure."""
        return sum(1 for r in self.results if r.error is not None)


def capture_environment() -> Environment:
    """Capture the runtime environment (Python version and platform), without a clock."""
    return Environment(python_version=platform.python_version(), platform=sys.platform)


def run_id(detector: DetectorInfo, split: str, config_hash: str, dataset_ids: Iterable[str]) -> str:
    """Return a deterministic run identifier (no clock; a hash of the run's identity)."""
    from synthaudit_bench.canonical import content_hash

    return content_hash(
        {
            "detector": detector.name,
            "version": detector.version,
            "split": split,
            "config_hash": config_hash,
            "datasets": sorted(dataset_ids),
        }
    )


def _detector_info(detector: Detector) -> DetectorInfo:
    caps = detector_capabilities(detector)
    return DetectorInfo(
        name=caps.name,
        version=caps.version,
        reference_free=caps.reference_free,
        capabilities=tuple(sorted(caps.sto_categories)),
        probe_family=caps.probe_family,
    )


def _status(result: AuditResult) -> str:
    return result.error.code if result.error is not None else "scored"


def run_benchmark(
    datasets: Iterable[Any],
    detector: Detector,
    *,
    split: str,
    bench_version: str = "1.0.0",
    sto_version: str = "1.0.0",
    schema_version: str = "1.0.0",
    config_hash: str = "",
    root_seed: int = 42,
    thresholds: Mapping[str, Any] | None = None,
    timeout_s: float | None = None,
    limits: ResourceLimits | None = None,
    environment: Environment | None = None,
    timestamps: Timestamps | None = None,
    mapper: OntologyMapper | None = None,
    cache: ResultCache | None = None,
    journal: Journal | None = None,
    jobs: int = 1,
    expected_hashes: Mapping[str, str] | None = None,
    should_cancel: Callable[[], bool] | None = None,
    validate: bool = True,
) -> RunOutcome:
    """Execute ``detector`` over ``datasets`` and return the results and manifest.

    Datasets are planned in sorted-by-id order with derived per-dataset seeds. A
    dataset whose content hash contradicts ``expected_hashes`` aborts the run
    (fail-closed integrity). Already-completed datasets present in a persistent
    cache are reused (resume). When ``should_cancel`` returns true, the remaining
    datasets are recorded as ``cancelled`` rather than executed. The manifest is
    validated against the run-manifest schema before it is returned.

    Raises:
        IntegrityAbort: if a dataset's content hash does not match its expected hash.
    """
    plan = plan_run(datasets, root_seed=root_seed)
    active_cache: ResultCache = cache if cache is not None else NullCache()
    events: list[RunEvent] = [RunEvent("run_start")]
    try:
        detector_info = _detector_info(detector)
    except Exception as exc:  # fail-open: capabilities() discovery must not abort the batch
        # Fall back to a minimal identity built from the type name. Every dataset
        # independently records the structured ``init`` failure via ``run_detector``
        # (which re-invokes ``capabilities()``), so the run completes with per-dataset
        # error records instead of terminating the whole batch here.
        detector_info = DetectorInfo(name=type(detector).__name__, version="unknown")
        events.append(RunEvent("detector_init_error", status=type(exc).__name__))

    expected = dict(expected_hashes or {})
    for item in plan:
        wanted = expected.get(item.dataset_id)
        if wanted is not None and item.content_hash != wanted.lower():
            raise IntegrityAbort(
                f"dataset {item.dataset_id!r} content hash {item.content_hash} "
                f"does not match expected {wanted.lower()}"
            )

    run_items: list[WorkItem] = []
    cancelled: list[WorkItem] = []
    stop = False
    for item in plan:
        if stop or (should_cancel is not None and should_cancel()):
            stop = True
            cancelled.append(item)
        else:
            run_items.append(item)

    def _compute(item: WorkItem) -> tuple[WorkItem, AuditResult, bool]:
        key = result_cache_key(
            item.content_hash, detector_info.name, detector_info.version, sto_version, config_hash
        )
        hit = active_cache.get(key)
        if hit is not None:
            # The cache is content-addressed; relabel the reused result with this
            # item's dataset id so per-dataset provenance stays correct even when two
            # datasets share byte-identical content (and therefore a cache key).
            return item, dataclasses.replace(hit, dataset_id=item.dataset_id), True
        context = ExecutionContext(
            seed=item.seed,
            bench_version=bench_version,
            sto_version=sto_version,
            thresholds=(
                MappingProxyType(dict(thresholds))
                if thresholds is not None
                else MappingProxyType({})
            ),
            timeout_s=timeout_s,
            config_hash=config_hash,
        )
        return item, run_detector(detector, item.dataset, context, mapper=mapper), False

    if jobs > 1 and run_items:
        with ThreadPoolExecutor(max_workers=jobs) as executor:
            computed = list(executor.map(_compute, run_items))
    else:
        computed = [_compute(item) for item in run_items]

    results: list[AuditResult] = []
    for item, result, was_cached in sorted(computed, key=lambda triple: triple[0].dataset_id):
        if not was_cached:
            key = result_cache_key(
                item.content_hash,
                detector_info.name,
                detector_info.version,
                sto_version,
                config_hash,
            )
            active_cache.put(key, result)
            if journal is not None:
                journal.append(item.dataset_id, result.content_hash())
        events.append(RunEvent("dataset_complete", item.dataset_id, _status(result), was_cached))
        results.append(result)

    for item in cancelled:
        result = AuditResult(
            dataset_id=item.dataset_id,
            dataset_sha256=item.content_hash,
            detector=detector_info,
            error=ErrorRecord("cancelled", "run cancelled before this dataset executed"),
        )
        events.append(RunEvent("dataset_cancelled", item.dataset_id, "cancelled"))
        results.append(result)

    results.sort(key=lambda r: r.dataset_id)
    events.append(RunEvent("run_complete"))

    manifest = RunManifest(
        bench_version=bench_version,
        sto_version=sto_version,
        schema_version=schema_version,
        split=split,
        detector=detector_info,
        config_hash=config_hash,
        environment=environment if environment is not None else capture_environment(),
        root_seed=root_seed,
        limits=limits if limits is not None else ResourceLimits(),
        timestamps=timestamps if timestamps is not None else Timestamps(_EPOCH, _EPOCH),
        datasets=tuple(
            DatasetEntry(r.dataset_id, r.dataset_sha256, _status(r), r.content_hash())
            for r in results
        ),
    )
    if validate:
        schemas.validate_instance("run-manifest", manifest.to_mapping())
    return RunOutcome(
        run_id=run_id(detector_info, split, config_hash, [r.dataset_id for r in results]),
        results=tuple(results),
        manifest=manifest,
        events=tuple(events),
    )


def write_artifacts(outcome: RunOutcome, out_dir: str | Path) -> dict[str, Path]:
    """Write per-dataset audit results and the run manifest under ``out_dir``.

    Produces ``<out_dir>/audits/<dataset_id>.json`` and ``<out_dir>/manifest.json``.
    Returns the manifest path and the audit directory.
    """
    root = Path(out_dir)
    audits = root / "audits"
    audits.mkdir(parents=True, exist_ok=True)
    for result in outcome.results:
        (audits / f"{result.dataset_id}.json").write_text(
            json.dumps(result.to_mapping(), sort_keys=True), encoding="utf-8"
        )
    manifest_path = root / "manifest.json"
    manifest_path.write_text(
        json.dumps(outcome.manifest.to_mapping(), sort_keys=True), encoding="utf-8"
    )
    return {"manifest": manifest_path, "audits": audits}
