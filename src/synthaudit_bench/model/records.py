"""The dataset metadata record and its embedded value objects.

``DatasetRecord`` mirrors the metadata record of specification Section 7. It is an
identity-bearing aggregate exposing the full serialization interface
(``from_mapping``/``to_mapping``/``to_canonical``/``content_hash``); the embedded
value objects (``License``, ``Source``, ``Transparency``, ``Loader``) are
serialization components without independent identity and expose
``from_mapping``/``to_mapping`` only.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from synthaudit_bench.model._canonical import canonical_bytes, hash_mapping
from synthaudit_bench.model.enums import (
    FrameStratum,
    GeneratorFamily,
    ProvenanceConfidence,
    Task,
)

__all__ = ["DatasetRecord", "License", "Loader", "Source", "Transparency"]


@dataclass(frozen=True, slots=True)
class License:
    """Redistribution terms for a dataset."""

    name: str
    redistribute: bool
    fetch_scriptable: bool
    spdx: str | None = None

    def to_mapping(self) -> dict[str, Any]:
        """Return the primitive mapping for this license."""
        mapping: dict[str, Any] = {
            "name": self.name,
            "redistribute": self.redistribute,
            "fetch_scriptable": self.fetch_scriptable,
        }
        if self.spdx is not None:
            mapping["spdx"] = self.spdx
        return mapping

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> License:
        """Build a license from a mapping."""
        return cls(
            name=data["name"],
            redistribute=bool(data["redistribute"]),
            fetch_scriptable=bool(data["fetch_scriptable"]),
            spdx=data.get("spdx"),
        )


@dataclass(frozen=True, slots=True)
class Source:
    """Provenance: source URLs, per-file checksums, and retrieval date."""

    urls: tuple[str, ...]
    sha256: Mapping[str, str]
    retrieved: str

    def to_mapping(self) -> dict[str, Any]:
        """Return the primitive mapping for this source."""
        return {
            "urls": list(self.urls),
            "sha256": {key: self.sha256[key] for key in sorted(self.sha256)},
            "retrieved": self.retrieved,
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> Source:
        """Build a source from a mapping."""
        return cls(
            urls=tuple(data["urls"]),
            sha256=MappingProxyType(dict(data["sha256"])),
            retrieved=data["retrieved"],
        )


@dataclass(frozen=True, slots=True)
class Transparency:
    """The four generator-disclosure booleans that feed the transparency pillar."""

    generator_described: bool
    generator_code_available: bool
    seed_reported: bool
    artifacts_disclosed: bool

    def to_mapping(self) -> dict[str, Any]:
        """Return the primitive mapping for these disclosures."""
        return {
            "generator_described": self.generator_described,
            "generator_code_available": self.generator_code_available,
            "seed_reported": self.seed_reported,
            "artifacts_disclosed": self.artifacts_disclosed,
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> Transparency:
        """Build a transparency record from a mapping."""
        return cls(
            generator_described=bool(data["generator_described"]),
            generator_code_available=bool(data["generator_code_available"]),
            seed_reported=bool(data["seed_reported"]),
            artifacts_disclosed=bool(data["artifacts_disclosed"]),
        )


@dataclass(frozen=True, slots=True)
class Loader:
    """A declarative parse specification for a dataset's files."""

    format: str
    header: str | int | None = None
    columns_ref: str | None = None
    options: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def to_mapping(self) -> dict[str, Any]:
        """Return the primitive mapping for this loader spec."""
        return {
            "format": self.format,
            "header": self.header,
            "columns_ref": self.columns_ref,
            "options": {key: self.options[key] for key in sorted(self.options)},
        }

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> Loader:
        """Build a loader spec from a mapping."""
        return cls(
            format=data["format"],
            header=data.get("header"),
            columns_ref=data.get("columns_ref"),
            options=MappingProxyType(dict(data.get("options", {}))),
        )


@dataclass(frozen=True, slots=True)
class DatasetRecord:
    """A dataset metadata record (specification Section 7).

    The stable identifier is ``id``; the content identity is ``content_hash()``.
    Optional scalar fields are omitted from the canonical mapping when ``None``.
    """

    id: str
    title: str
    frame_stratum: FrameStratum
    domain: str
    generator_family: GeneratorFamily
    provenance_confidence: ProvenanceConfidence
    task: Task
    target: str | None
    license: License
    source: Source
    loader: Loader
    transparency: Transparency
    citation: str
    secondary_domains: tuple[str, ...] = ()
    secondary_targets: tuple[str, ...] = ()
    modality: str = "tabular"
    generator_tool: str | None = None
    generation_date: str | None = None
    generator_version: str | None = None
    test_split: str | None = None
    notes: str | None = None

    def to_mapping(self) -> dict[str, Any]:
        """Return the fully primitive canonical mapping for this record."""
        mapping: dict[str, Any] = {
            "id": self.id,
            "title": self.title,
            "frame_stratum": self.frame_stratum.value,
            "domain": self.domain,
            "secondary_domains": list(self.secondary_domains),
            "generator_family": self.generator_family.value,
            "provenance_confidence": self.provenance_confidence.value,
            "modality": self.modality,
            "task": self.task.value,
            "target": self.target,
            "secondary_targets": list(self.secondary_targets),
            "license": self.license.to_mapping(),
            "source": self.source.to_mapping(),
            "loader": self.loader.to_mapping(),
            "transparency": self.transparency.to_mapping(),
            "citation": self.citation,
        }
        optionals = (
            ("generator_tool", self.generator_tool),
            ("generation_date", self.generation_date),
            ("generator_version", self.generator_version),
            ("test_split", self.test_split),
            ("notes", self.notes),
        )
        for key, value in optionals:
            if value is not None:
                mapping[key] = value
        return mapping

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> DatasetRecord:
        """Build a record from a mapping (assumed already schema-valid)."""
        return cls(
            id=data["id"],
            title=data["title"],
            frame_stratum=FrameStratum(data["frame_stratum"]),
            domain=data["domain"],
            generator_family=GeneratorFamily(data["generator_family"]),
            provenance_confidence=ProvenanceConfidence(data["provenance_confidence"]),
            task=Task(data["task"]),
            target=data.get("target"),
            license=License.from_mapping(data["license"]),
            source=Source.from_mapping(data["source"]),
            loader=Loader.from_mapping(data["loader"]),
            transparency=Transparency.from_mapping(data["transparency"]),
            citation=data["citation"],
            secondary_domains=tuple(data.get("secondary_domains", ())),
            secondary_targets=tuple(data.get("secondary_targets", ())),
            modality=data.get("modality", "tabular"),
            generator_tool=data.get("generator_tool"),
            generation_date=data.get("generation_date"),
            generator_version=data.get("generator_version"),
            test_split=data.get("test_split"),
            notes=data.get("notes"),
        )

    def to_canonical(self) -> bytes:
        """Return the deterministic canonical serialization."""
        return canonical_bytes(self.to_mapping())

    def content_hash(self) -> str:
        """Return the SHA-256 hex digest of the canonical serialization."""
        return hash_mapping(self.to_mapping())
