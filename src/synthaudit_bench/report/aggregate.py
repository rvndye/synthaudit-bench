"""Aggregate audit results into deterministic tidy tables and summaries.

These pure functions turn a run's :class:`~synthaudit_bench.model.results.AuditResult`
objects into long-format tidy rows (one row per finding, one per dataset) and into
per-dataset, per-detector, per-STO-class, and whole-benchmark summaries. Every row
set is sorted deterministically, so the same results always aggregate to the same
tables. Nothing here reads a clock or a global.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from synthaudit_bench.model.results import AuditResult, DetectorInfo
from synthaudit_bench.model.tuples import ArtifactTuple

__all__ = [
    "benchmark_summary",
    "dataset_rows",
    "finding_rows",
    "per_dataset_summary",
    "per_detector_summary",
    "sto_summary",
]


def _support_value(artifact: ArtifactTuple) -> Any:
    return artifact.support if isinstance(artifact.support, str) else sorted(artifact.support)


def finding_rows(results: Sequence[AuditResult]) -> tuple[dict[str, Any], ...]:
    """Return one tidy row per artifact across all results, deterministically ordered."""
    rows: list[dict[str, Any]] = []
    for result in sorted(results, key=lambda r: r.dataset_id):
        for artifact in result.tuples:
            rows.append(
                {
                    "dataset_id": result.dataset_id,
                    "sto_class": artifact.sto_class,
                    "support": _support_value(artifact),
                    "disposition": artifact.disposition.value if artifact.disposition else None,
                    "severity": artifact.severity.value if artifact.severity else None,
                    "confidence": artifact.confidence,
                }
            )
    return tuple(rows)


def dataset_rows(results: Sequence[AuditResult]) -> tuple[dict[str, Any], ...]:
    """Return one tidy row per dataset (id, hash, status, finding count)."""
    return tuple(
        {
            "dataset_id": result.dataset_id,
            "dataset_sha256": result.dataset_sha256,
            "status": result.error.code if result.error is not None else "scored",
            "n_findings": len(result.tuples),
            "error": result.error.code if result.error is not None else None,
        }
        for result in sorted(results, key=lambda r: r.dataset_id)
    )


def per_dataset_summary(results: Sequence[AuditResult]) -> tuple[dict[str, Any], ...]:
    """Return a per-dataset summary of status and finding count."""
    return tuple(
        {"dataset_id": row["dataset_id"], "status": row["status"], "n_findings": row["n_findings"]}
        for row in dataset_rows(results)
    )


def per_detector_summary(detector: DetectorInfo, results: Sequence[AuditResult]) -> dict[str, Any]:
    """Return a detector-level summary of datasets, scored/failed counts, and findings."""
    scored = sum(1 for r in results if r.error is None)
    failed = sum(1 for r in results if r.error is not None)
    return {
        "detector": detector.name,
        "version": detector.version,
        "n_datasets": len(results),
        "n_scored": scored,
        "n_failed": failed,
        "n_findings": sum(len(r.tuples) for r in results),
    }


def sto_summary(results: Sequence[AuditResult]) -> tuple[dict[str, Any], ...]:
    """Return per-STO-class counts and the number of datasets each class appears in."""
    counts: dict[str, int] = {}
    datasets: dict[str, set[str]] = {}
    for result in results:
        for artifact in result.tuples:
            counts[artifact.sto_class] = counts.get(artifact.sto_class, 0) + 1
            datasets.setdefault(artifact.sto_class, set()).add(result.dataset_id)
    return tuple(
        {"sto_class": sto_class, "count": counts[sto_class], "n_datasets": len(datasets[sto_class])}
        for sto_class in sorted(counts)
    )


def benchmark_summary(results: Sequence[AuditResult], *, split: str) -> dict[str, Any]:
    """Return a whole-benchmark summary for a split."""
    scored = sum(1 for r in results if r.error is None)
    classes = {artifact.sto_class for r in results for artifact in r.tuples}
    return {
        "split": split,
        "n_datasets": len(results),
        "n_scored": scored,
        "n_failed": len(results) - scored,
        "n_findings": sum(len(r.tuples) for r in results),
        "n_classes": len(classes),
    }
