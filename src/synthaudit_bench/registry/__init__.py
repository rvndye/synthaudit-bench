"""The registry and corpus-management subsystem (architecture ``registry`` module).

Loads and validates declarative dataset metadata records, organizes them by
corpus (census, evaluation, controlled, conformance) and evaluation split
(public-dev, held-out), and exposes deterministic enumeration, lookup, filtering,
indexing, and referential-integrity checking. It is metadata-only: it reads
registry files and never downloads data, loads tables, or runs detectors.
"""

from __future__ import annotations

from synthaudit_bench.registry.errors import (
    DuplicateIdError,
    IntegrityError,
    InvalidRecordError,
    RegistryError,
    UnknownDatasetError,
)
from synthaudit_bench.registry.integrity import referential_integrity, validate_registry
from synthaudit_bench.registry.loader import build_registry, load_registry
from synthaudit_bench.registry.model import (
    Corpus,
    IntegrityIssue,
    IntegrityReport,
    Registry,
    RegistryEntry,
    RegistryIndex,
    Split,
)
from synthaudit_bench.registry.query import (
    enumerate_corpus,
    filter_registry,
    get_dataset,
    list_datasets,
    registry_index,
)

__all__ = [
    "Corpus",
    "DuplicateIdError",
    "IntegrityError",
    "IntegrityIssue",
    "IntegrityReport",
    "InvalidRecordError",
    "Registry",
    "RegistryEntry",
    "RegistryError",
    "RegistryIndex",
    "Split",
    "UnknownDatasetError",
    "build_registry",
    "enumerate_corpus",
    "filter_registry",
    "get_dataset",
    "list_datasets",
    "load_registry",
    "referential_integrity",
    "registry_index",
    "validate_registry",
]
