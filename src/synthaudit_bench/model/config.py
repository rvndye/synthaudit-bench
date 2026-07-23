"""The resolved run configuration and its embedded value objects.

``Config`` is the fully resolved configuration for a run: the root seed, the
version pins, the resolved thresholds, the resource limits in force, and the
provenance of the configuration layers that produced it (architecture Section 8;
benchmark spec Section 9). Its content hash is the *config hash* recorded in run
manifests and used in cache keys, so two runs configured identically hash
identically. Every field participates in identity.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from synthaudit_bench.model._canonical import canonical_bytes, hash_mapping

__all__ = ["Config", "Pins", "ResourceLimits"]


@dataclass(frozen=True, slots=True)
class ResourceLimits:
    """Per-dataset wall-clock and memory limits in force for a run (spec Section 9.7)."""

    wall_clock_s: float | None = None
    memory_mb: int | None = None

    def to_mapping(self) -> dict[str, Any]:
        """Return the primitive mapping for these limits; unset limits are omitted."""
        mapping: dict[str, Any] = {}
        if self.wall_clock_s is not None:
            mapping["wall_clock_s"] = self.wall_clock_s
        if self.memory_mb is not None:
            mapping["memory_mb"] = self.memory_mb
        return mapping

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> ResourceLimits:
        """Build resource limits from a mapping."""
        return cls(
            wall_clock_s=data.get("wall_clock_s"),
            memory_mb=data.get("memory_mb"),
        )


@dataclass(frozen=True, slots=True)
class Pins:
    """Immutable version pins for a run (architecture Section 8: version pinning)."""

    bench_version: str
    sto_version: str
    schema_versions: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    synthaudit_version: str | None = None
    thresholds_ref: str | None = None

    def to_mapping(self) -> dict[str, Any]:
        """Return the primitive mapping for these pins."""
        mapping: dict[str, Any] = {
            "bench_version": self.bench_version,
            "sto_version": self.sto_version,
            "schema_versions": {k: self.schema_versions[k] for k in sorted(self.schema_versions)},
        }
        if self.synthaudit_version is not None:
            mapping["synthaudit_version"] = self.synthaudit_version
        if self.thresholds_ref is not None:
            mapping["thresholds_ref"] = self.thresholds_ref
        return mapping

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> Pins:
        """Build pins from a mapping."""
        return cls(
            bench_version=data["bench_version"],
            sto_version=data["sto_version"],
            schema_versions=MappingProxyType(dict(data.get("schema_versions", {}))),
            synthaudit_version=data.get("synthaudit_version"),
            thresholds_ref=data.get("thresholds_ref"),
        )


@dataclass(frozen=True, slots=True)
class Config:
    """A fully resolved, immutable run configuration."""

    pins: Pins
    root_seed: int = 42
    thresholds: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    limits: ResourceLimits = field(default_factory=ResourceLimits)
    layers: tuple[str, ...] = ()
    jobs: int | None = None
    log_level: str | None = None
    allow_pin_override: bool = False

    def to_mapping(self) -> dict[str, Any]:
        """Return the full primitive mapping for this configuration."""
        mapping: dict[str, Any] = {
            "pins": self.pins.to_mapping(),
            "root_seed": self.root_seed,
            "thresholds": dict(self.thresholds),
            "limits": self.limits.to_mapping(),
            "layers": list(self.layers),
            "allow_pin_override": self.allow_pin_override,
        }
        if self.jobs is not None:
            mapping["jobs"] = self.jobs
        if self.log_level is not None:
            mapping["log_level"] = self.log_level
        return mapping

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> Config:
        """Build a configuration from a mapping (assumed already schema-valid)."""
        return cls(
            pins=Pins.from_mapping(data["pins"]),
            root_seed=int(data.get("root_seed", 42)),
            thresholds=MappingProxyType(dict(data.get("thresholds", {}))),
            limits=ResourceLimits.from_mapping(data.get("limits", {})),
            layers=tuple(data.get("layers", ())),
            jobs=data.get("jobs"),
            log_level=data.get("log_level"),
            allow_pin_override=bool(data.get("allow_pin_override", False)),
        )

    def to_canonical(self) -> bytes:
        """Return the canonical serialization of the configuration."""
        return canonical_bytes(self.to_mapping())

    def content_hash(self) -> str:
        """Return the SHA-256 config hash used in manifests and cache keys."""
        return hash_mapping(self.to_mapping())
