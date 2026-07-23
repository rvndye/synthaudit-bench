"""The declarative figure specification and its embedded input value object.

``FigureSpec`` is a declarative, deterministic description of one figure
(architecture Section 12): its id, kind, the tidy-table inputs and columns it
consumes, the visual encoding, a caption, and free-form render parameters.
Rendering is out of scope for the domain layer; a spec is a pure, hashable
description. Every field participates in identity.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from synthaudit_bench.model._canonical import canonical_bytes, hash_mapping

__all__ = ["FigureInput", "FigureSpec"]


@dataclass(frozen=True, slots=True)
class FigureInput:
    """One tidy table and the columns a figure consumes from it."""

    table: str
    columns: tuple[str, ...] = ()

    def to_mapping(self) -> dict[str, Any]:
        """Return the primitive mapping for this input."""
        return {"table": self.table, "columns": list(self.columns)}

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> FigureInput:
        """Build a figure input from a mapping."""
        return cls(table=data["table"], columns=tuple(data.get("columns", ())))


@dataclass(frozen=True, slots=True)
class FigureSpec:
    """A declarative specification for one deterministic figure."""

    id: str
    kind: str
    caption: str
    inputs: tuple[FigureInput, ...] = ()
    encoding: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    params: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def to_mapping(self) -> dict[str, Any]:
        """Return the full primitive mapping for this figure specification."""
        return {
            "id": self.id,
            "kind": self.kind,
            "caption": self.caption,
            "inputs": [i.to_mapping() for i in self.inputs],
            "encoding": {k: self.encoding[k] for k in sorted(self.encoding)},
            "params": dict(self.params),
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> FigureSpec:
        """Build a figure specification from a mapping."""
        return cls(
            id=data["id"],
            kind=data["kind"],
            caption=data["caption"],
            inputs=tuple(FigureInput.from_mapping(i) for i in data.get("inputs", ())),
            encoding=MappingProxyType(dict(data.get("encoding", {}))),
            params=MappingProxyType(dict(data.get("params", {}))),
        )

    def to_canonical(self) -> bytes:
        """Return the canonical serialization of this figure specification."""
        return canonical_bytes(self.to_mapping())

    def content_hash(self) -> str:
        """Return the SHA-256 spec hash of this figure specification."""
        return hash_mapping(self.to_mapping())
