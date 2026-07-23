"""Immutable registry objects: corpus and split enums, entries, index, registry.

A :class:`Registry` is a frozen, deterministically ordered collection of
:class:`RegistryEntry` objects (each a dataset metadata record plus its corpus,
split, and optional content hash) with a precomputed :class:`RegistryIndex` for
efficient lookup. Every enumeration returns entries sorted by identifier, so the
result never depends on filesystem or insertion order.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from synthaudit_bench.model.enums import GeneratorFamily, ProvenanceConfidence, Task
from synthaudit_bench.model.records import DatasetRecord

__all__ = [
    "Corpus",
    "IntegrityIssue",
    "IntegrityReport",
    "Registry",
    "RegistryEntry",
    "RegistryIndex",
    "Split",
]


class Corpus(StrEnum):
    """The corpus a dataset belongs to."""

    CENSUS = "census"
    EVALUATION = "evaluation"
    CONTROLLED = "controlled"
    CONFORMANCE = "conformance"


class Split(StrEnum):
    """The evaluation-corpus split assignment (specification Section 6.3.3)."""

    PUBLIC_DEV = "public-dev"
    HELD_OUT = "held-out"


@dataclass(frozen=True, slots=True)
class RegistryEntry:
    """One dataset's metadata record with its corpus, split, and content hash."""

    record: DatasetRecord
    corpus: Corpus
    split: Split | None = None
    content_hash: str | None = None

    @property
    def id(self) -> str:
        """Return the dataset identifier."""
        return self.record.id

    def to_mapping(self) -> dict[str, Any]:
        """Return the primitive mapping for this entry."""
        mapping: dict[str, Any] = {"corpus": self.corpus.value, "record": self.record.to_mapping()}
        if self.split is not None:
            mapping["split"] = self.split.value
        if self.content_hash is not None:
            mapping["content_hash"] = self.content_hash
        return mapping


@dataclass(frozen=True, slots=True)
class RegistryIndex:
    """Precomputed, deterministic lookup maps over a registry."""

    by_id: Mapping[str, RegistryEntry]
    by_corpus: Mapping[str, tuple[str, ...]]
    by_split: Mapping[str, tuple[str, ...]]
    by_generator_family: Mapping[str, tuple[str, ...]]
    by_domain: Mapping[str, tuple[str, ...]]
    by_version: Mapping[str, tuple[str, ...]]
    by_content_hash: Mapping[str, str]

    def to_mapping(self) -> dict[str, Any]:
        """Return the deterministic primitive mapping for this index."""
        return {
            "ids": sorted(self.by_id),
            "by_corpus": {k: list(self.by_corpus[k]) for k in sorted(self.by_corpus)},
            "by_split": {k: list(self.by_split[k]) for k in sorted(self.by_split)},
            "by_generator_family": {
                k: list(self.by_generator_family[k]) for k in sorted(self.by_generator_family)
            },
            "by_domain": {k: list(self.by_domain[k]) for k in sorted(self.by_domain)},
            "by_version": {k: list(self.by_version[k]) for k in sorted(self.by_version)},
            "by_content_hash": {k: self.by_content_hash[k] for k in sorted(self.by_content_hash)},
        }


def _sorted(entries: tuple[RegistryEntry, ...]) -> tuple[RegistryEntry, ...]:
    return tuple(sorted(entries, key=lambda entry: entry.id))


@dataclass(frozen=True, slots=True)
class Registry:
    """An immutable, deterministically ordered registry of dataset records."""

    entries: tuple[RegistryEntry, ...]
    index: RegistryIndex

    def __len__(self) -> int:
        return len(self.entries)

    def __iter__(self) -> Iterator[RegistryEntry]:
        return iter(self.entries)

    def ids(self) -> tuple[str, ...]:
        """Return every dataset identifier in sorted order."""
        return tuple(sorted(self.index.by_id))

    def datasets(self) -> tuple[RegistryEntry, ...]:
        """Return every entry in deterministic (corpus, id) order."""
        return self.entries

    def contains(self, dataset_id: str) -> bool:
        """Return whether ``dataset_id`` is registered."""
        return dataset_id in self.index.by_id

    def get(self, dataset_id: str) -> RegistryEntry:
        """Return the entry for ``dataset_id``.

        Raises:
            UnknownDatasetError: if ``dataset_id`` is not registered.
        """
        from synthaudit_bench.registry.errors import UnknownDatasetError

        entry = self.index.by_id.get(dataset_id)
        if entry is None:
            raise UnknownDatasetError(f"unknown dataset: {dataset_id!r}")
        return entry

    def by_corpus(self, corpus: Corpus | str) -> tuple[RegistryEntry, ...]:
        """Return entries in ``corpus``, sorted by identifier."""
        value = Corpus(corpus)
        return _sorted(tuple(e for e in self.entries if e.corpus is value))

    def by_split(self, split: Split | str) -> tuple[RegistryEntry, ...]:
        """Return entries assigned to ``split``, sorted by identifier."""
        value = Split(split)
        return _sorted(tuple(e for e in self.entries if e.split is value))

    def by_generator_family(self, family: GeneratorFamily | str) -> tuple[RegistryEntry, ...]:
        """Return entries whose generator family is ``family``, sorted by identifier."""
        value = GeneratorFamily(family)
        return _sorted(tuple(e for e in self.entries if e.record.generator_family is value))

    def by_domain(self, domain: str) -> tuple[RegistryEntry, ...]:
        """Return entries whose primary domain is ``domain``, sorted by identifier."""
        return _sorted(tuple(e for e in self.entries if e.record.domain == domain))

    def by_task(self, task: Task | str) -> tuple[RegistryEntry, ...]:
        """Return entries whose task is ``task``, sorted by identifier."""
        value = Task(task)
        return _sorted(tuple(e for e in self.entries if e.record.task is value))

    def by_modality(self, modality: str) -> tuple[RegistryEntry, ...]:
        """Return entries whose modality is ``modality``, sorted by identifier."""
        return _sorted(tuple(e for e in self.entries if e.record.modality == modality))

    def by_license(self, license_name: str) -> tuple[RegistryEntry, ...]:
        """Return entries whose license name is ``license_name``, sorted by identifier."""
        return _sorted(tuple(e for e in self.entries if e.record.license.name == license_name))

    def by_provenance_confidence(
        self, confidence: ProvenanceConfidence | str
    ) -> tuple[RegistryEntry, ...]:
        """Return entries with the given provenance confidence, sorted by identifier."""
        value = ProvenanceConfidence(confidence)
        return _sorted(tuple(e for e in self.entries if e.record.provenance_confidence is value))

    def by_transparency(self, **flags: bool) -> tuple[RegistryEntry, ...]:
        """Return entries whose transparency flags all match, sorted by identifier.

        Each keyword is one of ``generator_described``, ``generator_code_available``,
        ``seed_reported``, ``artifacts_disclosed``.
        """
        return _sorted(
            tuple(
                e
                for e in self.entries
                if all(
                    getattr(e.record.transparency, name) is value for name, value in flags.items()
                )
            )
        )

    def filter(self, predicate: Callable[[RegistryEntry], bool]) -> tuple[RegistryEntry, ...]:
        """Return entries satisfying ``predicate``, sorted by identifier."""
        return _sorted(tuple(e for e in self.entries if predicate(e)))


@dataclass(frozen=True, slots=True)
class IntegrityIssue:
    """One referential-integrity violation."""

    code: str
    detail: str
    dataset_id: str | None = None

    def to_mapping(self) -> dict[str, Any]:
        """Return the primitive mapping for this issue."""
        return {"code": self.code, "detail": self.detail, "dataset_id": self.dataset_id}


@dataclass(frozen=True, slots=True)
class IntegrityReport:
    """The result of a referential-integrity check: ok plus any issues."""

    issues: tuple[IntegrityIssue, ...]

    @property
    def ok(self) -> bool:
        """Return whether the registry passed every integrity rule."""
        return not self.issues

    def to_mapping(self) -> dict[str, Any]:
        """Return the deterministic primitive mapping for this report."""
        return {"ok": self.ok, "issues": [issue.to_mapping() for issue in self.issues]}
