"""The per-dataset audit result and its detector and error value objects.

``AuditResult`` is one detector's output on one dataset. Its content identity
covers the substantive findings (dataset reference, detector, artifact tuples,
notes, error) and excludes the volatile ``runtime_s`` timing, so identical
findings hash identically across runs. Artifact tuples are normalized to
canonical sorted order on construction.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from synthaudit_bench.model._canonical import canonical_bytes, hash_mapping
from synthaudit_bench.model.tuples import ArtifactTuple

__all__ = ["AuditResult", "DetectorInfo", "ErrorRecord"]


@dataclass(frozen=True, slots=True)
class DetectorInfo:
    """Identity of the auditing system that produced a result."""

    name: str
    version: str
    reference_free: bool = True
    capabilities: tuple[str, ...] = ()
    probe_family: str | None = None

    def to_mapping(self) -> dict[str, Any]:
        """Return the primitive mapping for this detector."""
        mapping: dict[str, Any] = {
            "name": self.name,
            "version": self.version,
            "reference_free": self.reference_free,
        }
        if self.capabilities:
            mapping["capabilities"] = list(self.capabilities)
        if self.probe_family is not None:
            mapping["probe_family"] = self.probe_family
        return mapping

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> DetectorInfo:
        """Build a detector info from a mapping."""
        return cls(
            name=data["name"],
            version=data["version"],
            reference_free=bool(data.get("reference_free", True)),
            capabilities=tuple(data.get("capabilities", ())),
            probe_family=data.get("probe_family"),
        )


@dataclass(frozen=True, slots=True)
class ErrorRecord:
    """A structured dataset-level failure record."""

    code: str
    detail: str

    def to_mapping(self) -> dict[str, Any]:
        """Return the primitive mapping for this error."""
        return {"code": self.code, "detail": self.detail}

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> ErrorRecord:
        """Build an error record from a mapping."""
        return cls(code=data["code"], detail=data["detail"])


@dataclass(frozen=True, slots=True)
class AuditResult:
    """One detector's audit of one dataset."""

    dataset_id: str
    dataset_sha256: str
    detector: DetectorInfo
    tuples: tuple[ArtifactTuple, ...] = ()
    notes: tuple[str, ...] = ()
    error: ErrorRecord | None = None
    runtime_s: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "tuples", tuple(sorted(self.tuples)))

    def _identity_mapping(self) -> dict[str, Any]:
        mapping: dict[str, Any] = {
            "dataset_id": self.dataset_id,
            "dataset_sha256": self.dataset_sha256,
            "detector": self.detector.to_mapping(),
            "tuples": [t.to_mapping() for t in self.tuples],
            "notes": list(self.notes),
        }
        if self.error is not None:
            mapping["error"] = self.error.to_mapping()
        return mapping

    def to_mapping(self) -> dict[str, Any]:
        """Return the full primitive mapping, including run timing."""
        mapping = self._identity_mapping()
        mapping["runtime_s"] = self.runtime_s
        return mapping

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> AuditResult:
        """Build an audit result from a mapping (assumed already schema-valid)."""
        error = data.get("error")
        return cls(
            dataset_id=data["dataset_id"],
            dataset_sha256=data["dataset_sha256"],
            detector=DetectorInfo.from_mapping(data["detector"]),
            tuples=tuple(ArtifactTuple.from_mapping(t) for t in data.get("tuples", ())),
            notes=tuple(data.get("notes", ())),
            error=ErrorRecord.from_mapping(error) if error is not None else None,
            runtime_s=float(data.get("runtime_s", 0.0)),
        )

    def to_canonical(self) -> bytes:
        """Return the canonical serialization of the identity content."""
        return canonical_bytes(self._identity_mapping())

    def content_hash(self) -> str:
        """Return the SHA-256 of the identity content (excludes run timing)."""
        return hash_mapping(self._identity_mapping())
