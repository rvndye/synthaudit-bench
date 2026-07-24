"""Unit tests for detector-native to STO ontology mapping."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from synthaudit_bench.detector import build_ontology_mapper, identity_mapper, map_to_ontology
from synthaudit_bench.detector.errors import InvalidOntologyIdError
from synthaudit_bench.detector.ontology_map import _resolve
from synthaudit_bench.sto import ABSTAIN, UNCLASSIFIED


def test_exact_mapping_and_alias() -> None:
    mapper = build_ontology_mapper({"dup": "STO-A08"}, aliases={"duplicate": "dup"})
    assert mapper.map("dup") == "STO-A08"
    assert mapper.map("duplicate") == "STO-A08"


def test_native_sto_id_passthrough() -> None:
    assert map_to_ontology("STO-S02") == "STO-S02"


def test_reserved_symbols_pass_through() -> None:
    assert map_to_ontology(UNCLASSIFIED) == UNCLASSIFIED
    assert map_to_ontology(ABSTAIN) == ABSTAIN


def test_unknown_identifier_becomes_unclassified() -> None:
    assert map_to_ontology("totally-unknown") == UNCLASSIFIED
    # a well-formed but non-existent STO id is also unknown structure
    assert map_to_ontology("STO-Z99") == UNCLASSIFIED


def test_mapper_target_reserved_allowed() -> None:
    mapper = build_ontology_mapper({"skip": ABSTAIN})
    assert mapper.map("skip") == ABSTAIN


def test_build_rejects_unknown_target() -> None:
    with pytest.raises(InvalidOntologyIdError, match="not a known STO class"):
        build_ontology_mapper({"x": "STO-Z99"})


def test_build_rejects_malformed_target() -> None:
    with pytest.raises(InvalidOntologyIdError):
        build_ontology_mapper({"x": "not-an-id"})


def test_identity_mapper_and_to_mapping() -> None:
    mapper = identity_mapper()
    assert mapper.map("STO-A07") == "STO-A07"
    assert mapper.to_mapping()["sto_version"] == "1.0.0"
    assert mapper.map("nope") == UNCLASSIFIED


def test_mapper_passthrough_is_used_by_map_to_ontology() -> None:
    mapper = build_ontology_mapper({"n": "STO-S02"})
    assert map_to_ontology("n", mapper=mapper) == "STO-S02"


@dataclass
class _FakeOnto:
    """A tiny ontology stand-in to exercise deprecation resolution."""

    known: frozenset[str]
    deprecated: frozenset[str]
    replacements: dict[str, str | None]

    def is_known(self, class_id: str) -> bool:
        return class_id in self.known

    def is_deprecated(self, class_id: str) -> bool:
        return class_id in self.deprecated

    def replacement(self, class_id: str) -> str | None:
        return self.replacements.get(class_id)


def test_resolve_deprecated_maps_to_replacement() -> None:
    onto = _FakeOnto(
        known=frozenset({"STO-A01", "STO-A02"}),
        deprecated=frozenset({"STO-A01"}),
        replacements={"STO-A01": "STO-A02"},
    )
    assert _resolve("STO-A01", {}, {}, onto) == "STO-A02"  # type: ignore[arg-type]


def test_resolve_deprecated_without_replacement_kept() -> None:
    onto = _FakeOnto(
        known=frozenset({"STO-A01"}),
        deprecated=frozenset({"STO-A01"}),
        replacements={"STO-A01": None},
    )
    assert _resolve("STO-A01", {}, {}, onto) == "STO-A01"  # type: ignore[arg-type]


def test_resolve_unknown_target_from_mapping_is_unclassified() -> None:
    onto = _FakeOnto(known=frozenset({"STO-A01"}), deprecated=frozenset(), replacements={})
    assert _resolve("native", {"native": "STO-A02"}, {}, onto) == UNCLASSIFIED  # type: ignore[arg-type]
