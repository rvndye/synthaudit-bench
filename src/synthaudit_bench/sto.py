"""Loader and read-only API for the Structural Trustworthiness Ontology (STO).

Loads a pinned ontology version from package data, validates it against the STO
schema, and exposes an immutable, deterministic class register with lookup,
versioning, and deprecation queries.

The ontology is a standalone standard: this module depends only on the standard
library, ``jsonschema`` (via :mod:`synthaudit_bench.schemas`), and the domain
model. It never imports the SynthAudit reference implementation.

Example:
    >>> from synthaudit_bench import sto
    >>> onto = sto.load()
    >>> onto.get("STO-A07").name
    'Threshold or sign label'
    >>> onto.is_objective("STO-A07")
    True
    >>> onto.is_objective("STO-A06")   # rule-derived labels are adjudicated
    False
"""

from __future__ import annotations

import csv
import io
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from importlib import resources
from types import MappingProxyType
from typing import Any

from synthaudit_bench import schemas
from synthaudit_bench.errors import OntologyError
from synthaudit_bench.model import (
    ArtifactGroup,
    ClassDef,
    ColumnRole,
    Deprecation,
    Disposition,
    GoldType,
    Version,
)

__all__ = [
    "ABSTAIN",
    "DEFAULT_VERSION",
    "UNCLASSIFIED",
    "Ontology",
    "available_versions",
    "load",
]

_DATA_PACKAGE = "synthaudit_bench.sto_data"
_SCHEMA_NAME = "sto.schema.json"

DEFAULT_VERSION = "1.0.0"
UNCLASSIFIED = "STO-X00"
ABSTAIN = "ABSTAIN"
_RESERVED = frozenset({UNCLASSIFIED, ABSTAIN})
_STO_TOKEN = re.compile(r"STO-[A-Z][0-9]{2}")


@dataclass(frozen=True, slots=True)
class Ontology:
    """An immutable, validated Structural Trustworthiness Ontology.

    Build one with :func:`load`. All mappings are read-only proxies and all
    sequences are tuples, so an ``Ontology`` cannot be mutated after loading.
    """

    version: Version
    released: str
    title: str
    groups: Mapping[str, str]
    classes: Mapping[str, ClassDef]
    dispositions: Mapping[Disposition, str]
    roles: Mapping[ColumnRole, str]
    role_precedence: tuple[ColumnRole, ...]
    reserved_symbols: Mapping[str, str]
    compatibility: str
    extension_policy: str
    traceability: Mapping[str, str]

    def get(self, class_id: str) -> ClassDef:
        """Return the class definition for ``class_id``.

        Raises:
            OntologyError: if ``class_id`` is not a known class (reserved output
                symbols such as ``STO-X00`` and ``ABSTAIN`` are not classes).
        """
        try:
            return self.classes[class_id]
        except KeyError:
            raise OntologyError(f"unknown STO class: {class_id!r}") from None

    def is_known(self, class_id: str) -> bool:
        """Whether ``class_id`` is a defined class in this ontology."""
        return class_id in self.classes

    @staticmethod
    def is_reserved(symbol: str) -> bool:
        """Whether ``symbol`` is a reserved output token (not a class)."""
        return symbol in _RESERVED

    @property
    def class_ids(self) -> tuple[str, ...]:
        """The class identifiers in register (file) order."""
        return tuple(self.classes)

    def classes_in_group(self, group: ArtifactGroup) -> tuple[ClassDef, ...]:
        """All classes belonging to ``group``, in register order."""
        return tuple(c for c in self.classes.values() if c.group is group)

    def is_objective(self, class_id: str) -> bool:
        """Whether the class has objective (machine-verifiable) ground truth."""
        return self.get(class_id).is_objective

    def gold_type(self, class_id: str) -> GoldType:
        """The gold type of the class."""
        return self.get(class_id).gold_type

    def is_deprecated(self, class_id: str) -> bool:
        """Whether the class is deprecated."""
        return self.get(class_id).is_deprecated

    def replacement(self, class_id: str) -> str | None:
        """The replacement class id for a deprecated class, else ``None``."""
        deprecation = self.get(class_id).deprecation
        return deprecation.replaced_by if deprecation is not None else None

    def traceability_for(self, class_id: str) -> str | None:
        """The SynthAudit output field that realizes ``class_id``, if mapped.

        This documents the reference implementation only; the value is an opaque
        field reference, and importing SynthAudit is never required.
        """
        return self.traceability.get(class_id)

    @classmethod
    def from_mapping(
        cls, data: Mapping[str, Any], traceability: Mapping[str, str] | None = None
    ) -> Ontology:
        """Build an ontology from a decoded register mapping.

        The mapping is assumed to have passed JSON Schema validation. This method
        performs the additional structural checks the schema cannot express.

        Raises:
            OntologyError: on a structural inconsistency (duplicate class id, a
                relationship or replacement referencing an unknown class, or a
                role-precedence list that does not cover every column role).
        """
        classes: dict[str, ClassDef] = {}
        for raw in data["classes"]:
            cdef = _class_from_mapping(raw)
            if cdef.id in classes:
                raise OntologyError(f"duplicate STO class id: {cdef.id}")
            classes[cdef.id] = cdef

        known = set(classes)
        for cdef in classes.values():
            for text in cdef.relationships:
                for token in _STO_TOKEN.findall(text):
                    if token not in known and token not in _RESERVED:
                        raise OntologyError(
                            f"{cdef.id} relationship references unknown class: {token}"
                        )
            deprecation = cdef.deprecation
            if (
                deprecation is not None
                and deprecation.replaced_by is not None
                and deprecation.replaced_by not in known
            ):
                raise OntologyError(
                    f"{cdef.id} deprecation replaced_by references unknown class: "
                    f"{deprecation.replaced_by}"
                )

        role_precedence = tuple(ColumnRole(role) for role in data["role_precedence"])
        if set(role_precedence) != set(ColumnRole):
            raise OntologyError("role_precedence must cover every column role exactly once")

        return cls(
            version=Version.parse(data["sto_version"]),
            released=data["released"],
            title=data["title"],
            groups=MappingProxyType(dict(data["groups"])),
            classes=MappingProxyType(classes),
            dispositions=MappingProxyType(
                {Disposition(key): value for key, value in data["dispositions"].items()}
            ),
            roles=MappingProxyType(
                {ColumnRole(key): value for key, value in data["roles"].items()}
            ),
            role_precedence=role_precedence,
            reserved_symbols=MappingProxyType(dict(data["reserved_output_symbols"])),
            compatibility=data["compatibility"],
            extension_policy=data["extension_policy"],
            traceability=MappingProxyType(dict(traceability or {})),
        )


def _class_from_mapping(raw: Mapping[str, Any]) -> ClassDef:
    raw_deprecation = raw["deprecation"]
    deprecation = (
        None
        if raw_deprecation is None
        else Deprecation(
            since_version=raw_deprecation["since_version"],
            replaced_by=raw_deprecation["replaced_by"],
            reason=raw_deprecation["reason"],
        )
    )
    return ClassDef(
        id=raw["id"],
        name=raw["name"],
        group=ArtifactGroup(raw["group"]),
        gold_type=GoldType(raw["gold_type"]),
        definition=raw["definition"],
        scope=raw["scope"],
        inclusion_criteria=raw["inclusion_criteria"],
        exclusion_criteria=raw["exclusion_criteria"],
        example=raw["example"],
        counterexample=raw["counterexample"],
        relationships=tuple(raw["relationships"]),
        operating_points=tuple(raw["operating_points"]),
        deprecation=deprecation,
    )


def _read_json(name: str) -> Any:
    resource = resources.files(_DATA_PACKAGE) / name
    return json.loads(resource.read_text(encoding="utf-8"))


def _read_traceability(name: str = "traceability.csv") -> dict[str, str]:
    text = (resources.files(_DATA_PACKAGE) / name).read_text(encoding="utf-8")
    reader = csv.DictReader(io.StringIO(text))
    return {str(row["sto_class"]): str(row["synthaudit_field"]) for row in reader}


def _require_complete_traceability(ontology: Ontology) -> Ontology:
    """Guard that every class has a traceability entry.

    Raises:
        OntologyError: if any class lacks a SynthAudit-field mapping.
    """
    missing = [cid for cid in ontology.class_ids if cid not in ontology.traceability]
    if missing:
        raise OntologyError(f"traceability incomplete; missing: {', '.join(missing)}")
    return ontology


def _require_declared_version(ontology: Ontology, requested: str) -> Ontology:
    """Guard that a loaded register declares the version its filename requested.

    Raises:
        OntologyError: if the declared version differs from ``requested``.
    """
    if str(ontology.version) != requested:
        raise OntologyError(
            f"version mismatch: file STO-{requested}.json declares {ontology.version}"
        )
    return ontology


@cache
def load(version: str = DEFAULT_VERSION) -> Ontology:
    """Load and validate a pinned STO version from package data.

    The result is cached (the ontology is read and validated once per version).
    Loading is deterministic: the same version always yields an equal ontology.

    Raises:
        OntologyError: if ``version`` is not available or the register declares a
            version other than the one requested.
        SchemaError: if the register fails schema validation.
    """
    register_resource = resources.files(_DATA_PACKAGE) / f"STO-{version}.json"
    if not register_resource.is_file():
        raise OntologyError(f"unknown STO version: {version!r}")
    schema = _read_json(_SCHEMA_NAME)
    register = json.loads(register_resource.read_text(encoding="utf-8"))
    schemas.validate(register, schema, label=f"STO-{version}")
    ontology = Ontology.from_mapping(register, _read_traceability())
    _require_declared_version(ontology, version)
    return _require_complete_traceability(ontology)


def available_versions() -> tuple[str, ...]:
    """Return the sorted STO versions available as package data."""
    versions: list[str] = []
    for entry in resources.files(_DATA_PACKAGE).iterdir():
        name = entry.name
        if name.startswith("STO-") and name.endswith(".json"):
            versions.append(name[len("STO-") : -len(".json")])
    return tuple(sorted(versions))
