"""Mapping detector-native finding identifiers to STO class identifiers.

A detector names artifacts in its own vocabulary; the benchmark scores STO
identifiers (specification Section 4). This module resolves the former into the
latter following the frozen ontology: exact mappings, aliases for alternate
spellings, automatic resolution of a deprecated class to its replacement, and
binding to a specific ontology version. Any identifier that resolves to no known
class becomes ``STO-X00`` (unclassified), which the benchmark scores as an
abstention and never as a false positive (specification Sections 5.9 E-3, 4.1 P4).

A mapping table is validated when it is built: a table that targets an identifier
which is not a valid, known STO class fails closed with
:class:`~synthaudit_bench.detector.errors.InvalidOntologyIdError`.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from synthaudit_bench import sto
from synthaudit_bench.detector.errors import InvalidOntologyIdError
from synthaudit_bench.sto import ABSTAIN, DEFAULT_VERSION, UNCLASSIFIED, Ontology

__all__ = [
    "OntologyMapper",
    "build_ontology_mapper",
    "identity_mapper",
    "map_to_ontology",
]

_CLASS_ID = re.compile(r"^STO-[A-Z][0-9]{2}$")
_RESERVED = frozenset({UNCLASSIFIED, ABSTAIN})


def _is_class_id(token: str) -> bool:
    return _CLASS_ID.match(token) is not None


def _resolve(
    token: str, mappings: Mapping[str, str], aliases: Mapping[str, str], onto: Ontology
) -> str:
    """Resolve a native token to a canonical STO identifier against ``onto``."""
    native = aliases.get(token, token)
    if native in mappings:
        target = mappings[native]
    elif native in _RESERVED:
        return native
    elif _is_class_id(native):
        target = native
    else:
        return UNCLASSIFIED
    if target in _RESERVED:
        return target
    if not onto.is_known(target):
        return UNCLASSIFIED
    if onto.is_deprecated(target):
        replacement = onto.replacement(target)
        if replacement is not None:
            return replacement
    return target


@dataclass(frozen=True, slots=True)
class OntologyMapper:
    """An immutable, version-bound resolver from native identifiers to STO ids."""

    mappings: Mapping[str, str]
    aliases: Mapping[str, str]
    sto_version: str

    def map(self, native_id: str) -> str:
        """Resolve ``native_id`` to an STO identifier (or ``STO-X00`` if unknown)."""
        return _resolve(native_id, self.mappings, self.aliases, sto.load(self.sto_version))

    def to_mapping(self) -> dict[str, object]:
        """Return the deterministic primitive mapping for this mapper."""
        return {
            "sto_version": self.sto_version,
            "mappings": {key: self.mappings[key] for key in sorted(self.mappings)},
            "aliases": {key: self.aliases[key] for key in sorted(self.aliases)},
        }


def build_ontology_mapper(
    mappings: Mapping[str, str] | None = None,
    *,
    aliases: Mapping[str, str] | None = None,
    sto_version: str = DEFAULT_VERSION,
) -> OntologyMapper:
    """Build and validate a mapper for ``sto_version``.

    Every target identifier in ``mappings`` must be a reserved symbol or a class
    that the ontology version knows; otherwise the table is malformed.

    Raises:
        InvalidOntologyIdError: if a mapping targets an unknown or ill-formed id.
        OntologyError: if ``sto_version`` is not available.
    """
    onto = sto.load(sto_version)
    resolved_mappings = dict(mappings or {})
    for native, target in resolved_mappings.items():
        if target in _RESERVED:
            continue
        if not _is_class_id(target) or not onto.is_known(target):
            raise InvalidOntologyIdError(
                f"mapping {native!r} -> {target!r} is not a known STO class in {sto_version}"
            )
    return OntologyMapper(
        mappings=MappingProxyType(resolved_mappings),
        aliases=MappingProxyType(dict(aliases or {})),
        sto_version=sto_version,
    )


def identity_mapper(sto_version: str = DEFAULT_VERSION) -> OntologyMapper:
    """Return a mapper with no table: native STO ids pass through, others abstain."""
    return build_ontology_mapper(sto_version=sto_version)


def map_to_ontology(
    native_id: str,
    *,
    mapper: OntologyMapper | None = None,
    sto_version: str = DEFAULT_VERSION,
) -> str:
    """Resolve one native identifier to an STO id, following the frozen ontology.

    With no ``mapper``, native STO identifiers pass through (deprecated classes
    resolve to their replacement) and any other token becomes ``STO-X00``.
    """
    if mapper is not None:
        return mapper.map(native_id)
    return _resolve(native_id, {}, {}, sto.load(sto_version))
