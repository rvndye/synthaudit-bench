"""The run manifest and its embedded provenance value objects.

``RunManifest`` is the reproducibility contract for a scored run (benchmark
spec Section 9.6): benchmark, STO, and schema versions; split; detector
identity; the config hash; the environment; per-dataset content hashes and
statuses; seeds; the resource limits in force; and run timestamps. Timestamps
are injected at the supervisor boundary and are EXCLUDED from the manifest's
content identity, so two runs producing identical results and provenance hash
identically regardless of when they ran.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from synthaudit_bench.model._canonical import canonical_bytes, hash_mapping
from synthaudit_bench.model.config import ResourceLimits
from synthaudit_bench.model.results import DetectorInfo

__all__ = ["DatasetEntry", "Environment", "RunManifest", "Timestamps"]


@dataclass(frozen=True, slots=True)
class Environment:
    """The language runtime and locked dependency versions for a run."""

    python_version: str
    platform: str
    dependencies: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))

    def to_mapping(self) -> dict[str, Any]:
        """Return the primitive mapping for this environment."""
        return {
            "python_version": self.python_version,
            "platform": self.platform,
            "dependencies": {k: self.dependencies[k] for k in sorted(self.dependencies)},
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> Environment:
        """Build an environment from a mapping."""
        return cls(
            python_version=data["python_version"],
            platform=data["platform"],
            dependencies=MappingProxyType(dict(data.get("dependencies", {}))),
        )

    def env_hash(self) -> str:
        """Return the SHA-256 of this environment's canonical mapping."""
        return hash_mapping(self.to_mapping())


@dataclass(frozen=True, slots=True)
class DatasetEntry:
    """A per-dataset provenance line: content hash, status, and optional result hash."""

    dataset_id: str
    sha256: str
    status: str
    result_hash: str | None = None

    def to_mapping(self) -> dict[str, Any]:
        """Return the primitive mapping for this entry."""
        mapping: dict[str, Any] = {
            "dataset_id": self.dataset_id,
            "sha256": self.sha256,
            "status": self.status,
        }
        if self.result_hash is not None:
            mapping["result_hash"] = self.result_hash
        return mapping

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> DatasetEntry:
        """Build a dataset entry from a mapping."""
        return cls(
            dataset_id=data["dataset_id"],
            sha256=data["sha256"],
            status=data["status"],
            result_hash=data.get("result_hash"),
        )


@dataclass(frozen=True, slots=True)
class Timestamps:
    """Run start and finish timestamps, injected at the boundary (excluded from identity)."""

    started_at: str
    finished_at: str

    def to_mapping(self) -> dict[str, Any]:
        """Return the primitive mapping for these timestamps."""
        return {"started_at": self.started_at, "finished_at": self.finished_at}

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> Timestamps:
        """Build timestamps from a mapping."""
        return cls(started_at=data["started_at"], finished_at=data["finished_at"])


@dataclass(frozen=True, slots=True)
class RunManifest:
    """The reproducibility manifest for one scored run (spec Section 9.6)."""

    bench_version: str
    sto_version: str
    schema_version: str
    split: str
    detector: DetectorInfo
    config_hash: str
    environment: Environment
    root_seed: int
    limits: ResourceLimits
    timestamps: Timestamps
    datasets: tuple[DatasetEntry, ...] = ()
    held_out_seeds: tuple[int, ...] = ()
    pin_overrides: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "datasets", tuple(sorted(self.datasets, key=lambda e: e.dataset_id))
        )

    def _identity_mapping(self) -> dict[str, Any]:
        mapping: dict[str, Any] = {
            "bench_version": self.bench_version,
            "sto_version": self.sto_version,
            "schema_version": self.schema_version,
            "split": self.split,
            "detector": self.detector.to_mapping(),
            "config_hash": self.config_hash,
            "environment": self.environment.to_mapping(),
            "root_seed": self.root_seed,
            "limits": self.limits.to_mapping(),
            "datasets": [d.to_mapping() for d in self.datasets],
        }
        if self.held_out_seeds:
            mapping["held_out_seeds"] = list(self.held_out_seeds)
        if self.pin_overrides:
            mapping["pin_overrides"] = list(self.pin_overrides)
        return mapping

    def to_mapping(self) -> dict[str, Any]:
        """Return the full primitive mapping, including the volatile timestamps."""
        mapping = self._identity_mapping()
        mapping["timestamps"] = self.timestamps.to_mapping()
        return mapping

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> RunManifest:
        """Build a run manifest from a mapping (assumed already schema-valid)."""
        return cls(
            bench_version=data["bench_version"],
            sto_version=data["sto_version"],
            schema_version=data["schema_version"],
            split=data["split"],
            detector=DetectorInfo.from_mapping(data["detector"]),
            config_hash=data["config_hash"],
            environment=Environment.from_mapping(data["environment"]),
            root_seed=int(data["root_seed"]),
            limits=ResourceLimits.from_mapping(data.get("limits", {})),
            timestamps=Timestamps.from_mapping(data["timestamps"]),
            datasets=tuple(DatasetEntry.from_mapping(d) for d in data.get("datasets", ())),
            held_out_seeds=tuple(data.get("held_out_seeds", ())),
            pin_overrides=tuple(data.get("pin_overrides", ())),
        )

    def to_canonical(self) -> bytes:
        """Return the canonical serialization of the identity content (no timestamps)."""
        return canonical_bytes(self._identity_mapping())

    def content_hash(self) -> str:
        """Return the SHA-256 manifest hash (excludes injected timestamps)."""
        return hash_mapping(self._identity_mapping())
