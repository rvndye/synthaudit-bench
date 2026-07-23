"""Structured errors for the registry and corpus-management subsystem.

All extend :class:`synthaudit_bench.errors.SynthAuditBenchError`. ``IntegrityError``
is the registry's referential-integrity failure (architecture error taxonomy);
the more specific subtypes let callers distinguish a duplicate identifier, a
schema-invalid record, or an unknown dataset lookup.
"""

from __future__ import annotations

from synthaudit_bench.errors import SynthAuditBenchError

__all__ = [
    "DuplicateIdError",
    "IntegrityError",
    "InvalidRecordError",
    "RegistryError",
    "UnknownDatasetError",
]


class RegistryError(SynthAuditBenchError):
    """A registry could not be loaded, validated, or queried."""


class InvalidRecordError(RegistryError):
    """A registry record is not valid against the normative dataset schema."""


class IntegrityError(RegistryError):
    """The registry violates a referential-integrity rule."""


class DuplicateIdError(IntegrityError):
    """Two registry records declare the same dataset identifier."""


class UnknownDatasetError(RegistryError):
    """A lookup referenced a dataset identifier not present in the registry."""
