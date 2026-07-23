"""Deterministic enumeration, lookup, and filtering over a loaded registry.

These are thin, detector-independent functions over an immutable
:class:`Registry`. Every result is sorted by dataset identifier, so enumeration
and filtering are always deterministic.
"""

from __future__ import annotations

from synthaudit_bench.model.enums import GeneratorFamily, ProvenanceConfidence, Task
from synthaudit_bench.registry.model import (
    Corpus,
    Registry,
    RegistryEntry,
    RegistryIndex,
    Split,
)

__all__ = [
    "enumerate_corpus",
    "filter_registry",
    "get_dataset",
    "list_datasets",
    "registry_index",
]


def list_datasets(
    registry: Registry,
    *,
    corpus: Corpus | str | None = None,
    split: Split | str | None = None,
) -> tuple[RegistryEntry, ...]:
    """Return datasets, optionally restricted to a corpus and/or split, sorted by id."""
    entries = registry.entries
    if corpus is not None:
        wanted = Corpus(corpus)
        entries = tuple(e for e in entries if e.corpus is wanted)
    if split is not None:
        wanted_split = Split(split)
        entries = tuple(e for e in entries if e.split is wanted_split)
    return tuple(sorted(entries, key=lambda e: e.id))


def get_dataset(registry: Registry, dataset_id: str) -> RegistryEntry:
    """Return the entry for ``dataset_id``.

    Raises:
        UnknownDatasetError: if ``dataset_id`` is not registered.
    """
    return registry.get(dataset_id)


def filter_registry(
    registry: Registry,
    *,
    corpus: Corpus | str | None = None,
    split: Split | str | None = None,
    generator_family: GeneratorFamily | str | None = None,
    domain: str | None = None,
    task: Task | str | None = None,
    modality: str | None = None,
    license_name: str | None = None,
    provenance_confidence: ProvenanceConfidence | str | None = None,
    transparency: dict[str, bool] | None = None,
) -> tuple[RegistryEntry, ...]:
    """Return datasets matching every supplied criterion, sorted by identifier."""
    corpus_v = Corpus(corpus) if corpus is not None else None
    split_v = Split(split) if split is not None else None
    family_v = GeneratorFamily(generator_family) if generator_family is not None else None
    task_v = Task(task) if task is not None else None
    confidence_v = (
        ProvenanceConfidence(provenance_confidence) if provenance_confidence is not None else None
    )
    flags = transparency or {}

    def _matches(entry: RegistryEntry) -> bool:
        record = entry.record
        return (
            (corpus_v is None or entry.corpus is corpus_v)
            and (split_v is None or entry.split is split_v)
            and (family_v is None or record.generator_family is family_v)
            and (domain is None or record.domain == domain)
            and (task_v is None or record.task is task_v)
            and (modality is None or record.modality == modality)
            and (license_name is None or record.license.name == license_name)
            and (confidence_v is None or record.provenance_confidence is confidence_v)
            and all(getattr(record.transparency, name) is value for name, value in flags.items())
        )

    return registry.filter(_matches)


def registry_index(registry: Registry) -> RegistryIndex:
    """Return the registry's precomputed lookup index."""
    return registry.index


def enumerate_corpus(registry: Registry, corpus: Corpus | str) -> tuple[RegistryEntry, ...]:
    """Return every dataset in ``corpus``, sorted by identifier."""
    return registry.by_corpus(corpus)
