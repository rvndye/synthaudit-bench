"""Deliverable 2: acquisition pipeline.

Drives the frozen ``synthaudit_bench.acquire.acquire_dataset`` over a set of dataset
records: it downloads through a caller-injected transport, applies the license gate,
verifies content integrity by SHA-256, stores provenance, and records every failure
as a structured entry. It fails closed. There is no silent recovery and no inferred
metadata: an integrity or license failure is reported, never worked around, and a
record with no obtainable data becomes an explicit stub or an explicit failure.

The pipeline ships no network code; the ``fetcher`` is injected by the caller (the
same discipline the frozen acquisition uses), so nothing is downloaded unless a
transport is wired in explicitly.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from synthaudit_bench.acquire import (
    AcquireError,
    ChecksumError,
    Fetcher,
    LicenseError,
    ResourceError,
    acquire_dataset,
)
from synthaudit_bench.model.records import DatasetRecord
from synthaudit_bench.registry.loader import load_registry

from benchkit.provenance import provenance_block

__all__ = ["AcquisitionOutcome", "AcquisitionReport", "acquire_records", "records_from_registry"]


@dataclass(frozen=True, slots=True)
class AcquisitionOutcome:
    """The outcome of acquiring one record."""

    dataset_id: str
    status: str  # "verified" | "stub" | "failed"
    files: tuple[str, ...] = ()
    verified: bool = False
    reason: str | None = None
    error_code: str | None = None

    def to_mapping(self) -> dict[str, Any]:
        """Return the deterministic primitive mapping for this outcome."""
        mapping: dict[str, Any] = {
            "dataset_id": self.dataset_id,
            "status": self.status,
            "verified": self.verified,
            "files": sorted(self.files),
        }
        if self.reason is not None:
            mapping["reason"] = self.reason
        if self.error_code is not None:
            mapping["error_code"] = self.error_code
        return mapping


@dataclass(frozen=True, slots=True)
class AcquisitionReport:
    """The report over an acquisition run."""

    outcomes: tuple[AcquisitionOutcome, ...]
    provenance: dict[str, Any]

    @property
    def ok(self) -> bool:
        """True when no record failed (stubs are a valid, non-failing outcome)."""
        return all(outcome.status != "failed" for outcome in self.outcomes)

    @property
    def failures(self) -> tuple[AcquisitionOutcome, ...]:
        """The failed outcomes, in id order."""
        return tuple(o for o in self.outcomes if o.status == "failed")

    def to_mapping(self) -> dict[str, Any]:
        """Return the deterministic primitive mapping for the report."""
        return {
            "ok": self.ok,
            "n_records": len(self.outcomes),
            "n_verified": sum(1 for o in self.outcomes if o.status == "verified"),
            "n_stub": sum(1 for o in self.outcomes if o.status == "stub"),
            "n_failed": len(self.failures),
            "outcomes": [o.to_mapping() for o in self.outcomes],
            "provenance": self.provenance,
        }


def records_from_registry(root: str | Path) -> list[DatasetRecord]:
    """Load dataset records from a registry tree (fails closed via the frozen loader)."""
    registry = load_registry(str(root))
    return [entry.record for entry in registry.datasets()]


def _acquire_one(
    record: DatasetRecord, cache_dir: Path, *, fetcher: Fetcher | None, require_data: bool
) -> AcquisitionOutcome:
    try:
        acquired = acquire_dataset(record, cache_dir, fetcher=fetcher, require_data=require_data)
    except ChecksumError as exc:
        return AcquisitionOutcome(record.id, "failed", reason=str(exc), error_code="integrity")
    except LicenseError as exc:
        return AcquisitionOutcome(record.id, "failed", reason=str(exc), error_code="license")
    except ResourceError as exc:
        return AcquisitionOutcome(record.id, "failed", reason=str(exc), error_code="resource")
    except AcquireError as exc:
        return AcquisitionOutcome(record.id, "failed", reason=str(exc), error_code="acquire")
    if acquired.is_stub:
        reason = acquired.stub.reason if acquired.stub is not None else "fetch stub"
        return AcquisitionOutcome(record.id, "stub", reason=reason)
    return AcquisitionOutcome(
        record.id,
        "verified",
        files=tuple(sorted(acquired.files)),
        verified=acquired.verified,
    )


def acquire_records(
    records: Iterable[DatasetRecord],
    cache_dir: str | Path,
    *,
    fetcher: Fetcher | None = None,
    require_data: bool = False,
    generated_at: str | None = None,
) -> AcquisitionReport:
    """Acquire ``records`` into ``cache_dir`` and return a structured report.

    Each record is acquired through the frozen path with the injected ``fetcher``.
    A checksum mismatch, a forbidden license, or an unobtainable required file becomes
    a structured ``failed`` outcome with an error code; a non-redistributable record
    with no fetcher becomes an explicit ``stub``; a verified acquisition lists its
    files. The report's ``ok`` is false if any record failed. Ordering is by id, so
    the report is deterministic.
    """
    cache = Path(cache_dir)
    ordered = sorted(records, key=lambda r: r.id)
    outcomes = tuple(
        _acquire_one(record, cache, fetcher=fetcher, require_data=require_data)
        for record in ordered
    )
    provenance = provenance_block(
        tool="acquire.records",
        inputs=[record.id for record in ordered],
        parameters={"require_data": require_data, "fetcher": fetcher is not None},
        generated_at=generated_at,
    )
    return AcquisitionReport(outcomes=outcomes, provenance=provenance)
