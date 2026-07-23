"""The schema subsystem: normative JSON Schemas, loading, and validation.

This package completes the architecture's ``schemas`` module. It ships the
normative Draft 2020-12 schemas as package data (specification Appendices A-C
plus the manifest, metrics, and configuration schemas, and the ontology
register schema), loads them into an immutable, cached registry, resolves
versions and cross-schema ``$ref`` references, and validates instances into
structured errors. The low-level primitives :func:`validate` (validate against
an explicit schema mapping) and :func:`check_schema` (schema well-formedness)
are retained unchanged from WP1; the named-schema API is layered on top.
"""

from __future__ import annotations

from typing import Any

from synthaudit_bench.schemas._primitives import check_schema, validate
from synthaudit_bench.schemas.errors import (
    InvalidSchemaError,
    SchemaCompatibilityError,
    SchemaValidationError,
    UnknownSchemaError,
)
from synthaudit_bench.schemas.registry import Schema, SchemaRegistry, default_registry

__all__ = [
    "InvalidSchemaError",
    "Schema",
    "SchemaCompatibilityError",
    "SchemaRegistry",
    "SchemaValidationError",
    "UnknownSchemaError",
    "check_schema",
    "default_registry",
    "get_schema",
    "list_schemas",
    "load_schema",
    "schema_version",
    "supported_versions",
    "validate",
    "validate_instance",
]


def load_schema(name: str, version: str | None = None) -> Schema:
    """Return the immutable :class:`Schema` handle for ``name`` (latest, or ``version``)."""
    return default_registry().load_schema(name, version)


def get_schema(name: str, version: str | None = None) -> dict[str, Any]:
    """Return a fresh copy of the resolved schema document for ``name``."""
    return default_registry().get_schema(name, version)


def validate_instance(name: str, instance: Any, version: str | None = None) -> None:
    """Validate ``instance`` against the named schema ``name`` (never mutates it).

    This is the named-schema validator of the schema-system public API. The bare
    :func:`validate` name is retained for the low-level explicit-schema primitive.

    Raises:
        UnknownSchemaError: if ``name`` is not registered.
        SchemaCompatibilityError: if no registered version satisfies ``version``.
        SchemaValidationError: if ``instance`` does not satisfy the schema.
    """
    default_registry().validate(name, instance, version)


def list_schemas() -> tuple[str, ...]:
    """Return every registered schema name, sorted."""
    return default_registry().list_schemas()


def schema_version(name: str, version: str | None = None) -> str:
    """Return the resolved version string of the named schema."""
    return default_registry().schema_version(name, version)


def supported_versions() -> tuple[str, ...]:
    """Return every distinct registered schema version, sorted ascending."""
    return default_registry().supported_versions()
