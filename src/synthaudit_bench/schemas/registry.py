"""The named-schema registry: discovery, loading, caching, and validation.

The registry owns the set of normative JSON Schemas (specification Appendices
A-C plus the manifest, metrics, and configuration schemas, and the ontology
register schema). It loads them deterministically from package data, exposes
immutable :class:`Schema` handles, resolves versions under the additive-minor
compatibility rule, resolves cross-schema ``$ref`` references, caches compiled
validators, and validates instances into structured errors. It never mutates a
validated instance and holds no state beyond memoized copies of immutable data.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from functools import cache
from importlib import resources
from typing import Any

from jsonschema.validators import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from synthaudit_bench.model.semver import Version
from synthaudit_bench.schemas._primitives import check_schema
from synthaudit_bench.schemas.errors import (
    InvalidSchemaError,
    SchemaCompatibilityError,
    SchemaValidationError,
    UnknownSchemaError,
)

__all__ = ["Schema", "SchemaRegistry", "default_registry"]

_SCHEMA_PACKAGE = "synthaudit_bench.schema_data"
_SCHEMA_SUFFIX = ".schema.json"
# The ontology (STO register) schema is owned by WP1 and lives in its data package.
_ONTOLOGY_NAME = "ontology"
_ONTOLOGY_PACKAGE = "synthaudit_bench.sto_data"
_ONTOLOGY_FILE = "sto.schema.json"


def _canonical_json(document: Mapping[str, Any]) -> str:
    """Serialize a schema document to deterministic, sorted-key JSON text."""
    return json.dumps(document, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _version_of(document: Mapping[str, Any]) -> Version:
    """Return the schema version from the ``version`` key, else from the ``$id`` path."""
    declared = document.get("version")
    if isinstance(declared, str):
        return Version.parse(declared)
    schema_id = str(document.get("$id", ""))
    for part in schema_id.split("/"):
        if part.startswith("v") and part[1:].replace(".", "").isdigit():
            major, _, rest = part[1:].partition(".")
            minor, _, patch = rest.partition(".")
            return Version(int(major), int(minor or 0), int(patch or 0))
    return Version(1, 0, 0)


@dataclass(frozen=True, slots=True)
class Schema:
    """An immutable, validated JSON Schema and its identity."""

    name: str
    version: Version
    schema_id: str
    json_text: str

    def as_dict(self) -> dict[str, Any]:
        """Return a fresh, mutable copy of the schema document.

        A new object is decoded on every call, so the registry's cached schema
        can never be mutated through a returned value.
        """
        document: dict[str, Any] = json.loads(self.json_text)
        return document


class SchemaRegistry:
    """A deterministic, cached registry of named normative schemas.

    Construct from an iterable of ``(name, document)`` pairs. Each document is
    checked as a Draft 2020-12 schema on registration; malformed schemas raise
    :class:`InvalidSchemaError`. Multiple versions of a name may be registered;
    :meth:`load_schema` resolves the requested version under the additive-minor
    compatibility rule.
    """

    def __init__(self, documents: Iterable[tuple[str, Mapping[str, Any]]]) -> None:
        by_name: dict[str, dict[Version, Schema]] = {}
        resources_by_id: dict[str, Resource[Any]] = {}
        validators: dict[tuple[str, Version], Draft202012Validator] = {}
        referencing_registry: Registry[Any] = Registry()

        for name, document in documents:
            try:
                check_schema(document)
            except Exception as exc:
                raise InvalidSchemaError(f"schema {name!r} is not valid: {exc}") from exc
            version = _version_of(document)
            schema_id = str(document.get("$id", name))
            schema = Schema(name, version, schema_id, _canonical_json(document))
            by_name.setdefault(name, {})[version] = schema
            if "$id" in document:
                resources_by_id[schema_id] = Resource.from_contents(
                    schema.as_dict(), default_specification=DRAFT202012
                )

        if resources_by_id:
            referencing_registry = referencing_registry.with_resources(resources_by_id.items())

        self._by_name = by_name
        self._referencing = referencing_registry
        self._validators = validators

    @classmethod
    def from_package_data(cls) -> SchemaRegistry:
        """Discover and load every packaged normative schema (deterministic)."""
        return cls(_discover_documents())

    def list_schemas(self) -> tuple[str, ...]:
        """Return the registered schema names in deterministic sorted order."""
        return tuple(sorted(self._by_name))

    def supported_versions(self) -> tuple[str, ...]:
        """Return every distinct registered schema version, sorted ascending."""
        versions = {v for versions in self._by_name.values() for v in versions}
        return tuple(str(v) for v in sorted(versions))

    def available_versions(self, name: str) -> tuple[str, ...]:
        """Return the registered versions of ``name``, sorted ascending."""
        versions = self._by_name.get(name)
        if versions is None:
            raise UnknownSchemaError(f"unknown schema: {name!r}")
        return tuple(str(v) for v in sorted(versions))

    def load_schema(self, name: str, version: str | None = None) -> Schema:
        """Resolve and return the :class:`Schema` for ``name``.

        With ``version`` omitted the latest registered version is returned. With
        ``version`` given, the highest registered version that satisfies it under
        the additive-minor rule is returned.

        Raises:
            UnknownSchemaError: if ``name`` is not registered.
            SchemaCompatibilityError: if no registered version satisfies ``version``.
        """
        return self._resolve(name, version)

    def schema_version(self, name: str, version: str | None = None) -> str:
        """Return the resolved version string for ``name``."""
        return str(self._resolve(name, version).version)

    def get_schema(self, name: str, version: str | None = None) -> dict[str, Any]:
        """Return a fresh copy of the resolved schema document for ``name``."""
        return self._resolve(name, version).as_dict()

    def is_compatible(self, name: str, version: str) -> bool:
        """Return whether some registered version of ``name`` satisfies ``version``."""
        versions = self._by_name.get(name)
        if versions is None:
            return False
        required = Version.parse(version)
        return any(available.satisfies(required) for available in versions)

    def validate(self, name: str, instance: Any, version: str | None = None) -> None:
        """Validate ``instance`` against the resolved schema ``name``.

        The instance is never mutated. On failure the first error, ordered
        deterministically by JSON pointer then message, is raised.

        Raises:
            UnknownSchemaError: if ``name`` is not registered.
            SchemaCompatibilityError: if no registered version satisfies ``version``.
            SchemaValidationError: if ``instance`` does not satisfy the schema.
        """
        schema = self._resolve(name, version)
        validator = self._validator_for(schema)
        errors = sorted(
            validator.iter_errors(instance),
            key=lambda err: ([str(part) for part in err.absolute_path], err.message),
        )
        if errors:
            first = errors[0]
            pointer = "/" + "/".join(str(part) for part in first.absolute_path)
            raise SchemaValidationError(
                schema_id=schema.schema_id,
                pointer=pointer,
                value=first.instance,
                explanation=first.message,
            )

    def _resolve(self, name: str, version: str | None) -> Schema:
        versions = self._by_name.get(name)
        if versions is None:
            raise UnknownSchemaError(f"unknown schema: {name!r}")
        if version is None:
            return versions[max(versions)]
        required = Version.parse(version)
        candidates = [available for available in versions if available.satisfies(required)]
        if not candidates:
            raise SchemaCompatibilityError(
                f"no registered version of {name!r} satisfies {version!r}; "
                f"available: {', '.join(str(v) for v in sorted(versions))}"
            )
        return versions[max(candidates)]

    def _validator_for(self, schema: Schema) -> Draft202012Validator:
        key = (schema.name, schema.version)
        validator = self._validators.get(key)
        if validator is None:
            validator = Draft202012Validator(schema.as_dict(), registry=self._referencing)
            self._validators[key] = validator
        return validator


def _discover_documents() -> list[tuple[str, Mapping[str, Any]]]:
    """Load every packaged schema document in deterministic (sorted) order."""
    documents: list[tuple[str, Mapping[str, Any]]] = []
    root = resources.files(_SCHEMA_PACKAGE)
    for entry in sorted(root.iterdir(), key=lambda item: item.name):
        if entry.name.endswith(_SCHEMA_SUFFIX):
            name = entry.name[: -len(_SCHEMA_SUFFIX)]
            documents.append((name, json.loads(entry.read_text(encoding="utf-8"))))
    ontology = resources.files(_ONTOLOGY_PACKAGE) / _ONTOLOGY_FILE
    documents.append((_ONTOLOGY_NAME, json.loads(ontology.read_text(encoding="utf-8"))))
    return documents


@cache
def default_registry() -> SchemaRegistry:
    """Return the process-wide registry of packaged schemas (built once, cached).

    The result is a pure function of the packaged schema data; the cache is
    memoization of immutable data, not mutable global state.
    """
    return SchemaRegistry.from_package_data()
