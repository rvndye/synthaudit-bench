"""Structured error taxonomy for SynthAudit-Bench.

Every error the library raises is one of these types, so callers can handle
failures exhaustively. WP1 introduces the ontology, schema, and version errors;
later work packages extend the taxonomy without redefining these.
"""

from __future__ import annotations

__all__ = [
    "OntologyError",
    "SchemaError",
    "SynthAuditBenchError",
    "VersionError",
]


class SynthAuditBenchError(Exception):
    """Base class for every error raised by SynthAudit-Bench."""


class SchemaError(SynthAuditBenchError):
    """An instance failed validation against its JSON Schema.

    The message identifies the failing location as a JSON pointer so failures are
    actionable and deterministic.
    """


class OntologyError(SynthAuditBenchError):
    """The Structural Trustworthiness Ontology is malformed, or a lookup failed.

    Raised for an unknown ontology version, a structurally inconsistent register
    (for example duplicate class identifiers), or a lookup of an unknown class.
    """


class VersionError(SynthAuditBenchError):
    """A version string is not a valid ``MAJOR.MINOR.PATCH`` triple."""
