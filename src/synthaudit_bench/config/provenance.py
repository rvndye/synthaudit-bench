"""Immutable provenance and the resolved-configuration result object.

``ResolvedConfig`` pairs the effective :class:`~synthaudit_bench.model.config.Config`
(the hashable resolved values) with a :class:`Provenance` record that traces how
every value was resolved: which layer set it, which values were overridden, the
profile and threshold version, the raw environment, CLI, and per-dataset
overrides, and any version-pin override events. Provenance is metadata about the
resolution, not part of the configuration hash; it is deterministic and
reproducible.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from synthaudit_bench.model.config import Config

__all__ = ["LayerContribution", "PinOverride", "Provenance", "ResolvedConfig"]


@dataclass(frozen=True, slots=True)
class LayerContribution:
    """One configuration layer and the resolved leaf paths it owns."""

    name: str
    source: str | None
    kind: str
    keys: tuple[str, ...]

    def to_mapping(self) -> dict[str, Any]:
        """Return the primitive mapping for this layer contribution."""
        return {
            "name": self.name,
            "source": self.source,
            "kind": self.kind,
            "keys": list(self.keys),
        }


@dataclass(frozen=True, slots=True)
class PinOverride:
    """A recorded event where a non-base layer changed a version pin."""

    path: str
    previous: Any
    new: Any
    layer: str

    def to_mapping(self) -> dict[str, Any]:
        """Return the primitive mapping for this pin-override event."""
        return {"path": self.path, "previous": self.previous, "new": self.new, "layer": self.layer}


@dataclass(frozen=True, slots=True)
class Provenance:
    """The complete, deterministic provenance of a resolved configuration."""

    layers: tuple[LayerContribution, ...]
    sources: Mapping[str, str]
    overridden: tuple[str, ...]
    profile: str | None
    threshold_version: str
    threshold_source: str
    env_overrides: Mapping[str, Any]
    cli_overrides: Mapping[str, Any]
    dataset_overrides: Mapping[str, Any]
    pin_overrides: tuple[PinOverride, ...]

    def to_mapping(self) -> dict[str, Any]:
        """Return the deterministic primitive mapping for this provenance."""
        return {
            "layers": [layer.to_mapping() for layer in self.layers],
            "sources": {key: self.sources[key] for key in sorted(self.sources)},
            "overridden": list(self.overridden),
            "profile": self.profile,
            "threshold_version": self.threshold_version,
            "threshold_source": self.threshold_source,
            "env_overrides": dict(self.env_overrides),
            "cli_overrides": dict(self.cli_overrides),
            "dataset_overrides": dict(self.dataset_overrides),
            "pin_overrides": [override.to_mapping() for override in self.pin_overrides],
        }


@dataclass(frozen=True, slots=True)
class ResolvedConfig:
    """The effective configuration plus its resolution provenance."""

    config: Config
    provenance: Provenance

    def config_hash(self) -> str:
        """Return the configuration hash (the effective values, excluding provenance)."""
        return self.config.content_hash()

    def to_mapping(self) -> dict[str, Any]:
        """Return the primitive mapping for the config and its provenance."""
        return {"config": self.config.to_mapping(), "provenance": self.provenance.to_mapping()}
