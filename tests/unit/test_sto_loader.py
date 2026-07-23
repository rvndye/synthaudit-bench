"""Unit tests for the ontology loader and lookup API."""

from __future__ import annotations

import pytest

from synthaudit_bench import sto
from synthaudit_bench.errors import OntologyError
from synthaudit_bench.model import ArtifactGroup, GoldType, Version


def test_load_default_version() -> None:
    onto = sto.load()
    assert str(onto.version) == "1.0.0"
    assert len(onto.class_ids) == 16


def test_get_and_unknown_class() -> None:
    onto = sto.load()
    assert onto.get("STO-A07").name == "Threshold or sign label"
    assert onto.is_known("STO-A07") is True
    assert onto.is_known("STO-Z99") is False
    with pytest.raises(OntologyError):
        onto.get("STO-Z99")


def test_reserved_symbols_are_not_classes() -> None:
    onto = sto.load()
    assert sto.Ontology.is_reserved("STO-X00") is True
    assert sto.Ontology.is_reserved("ABSTAIN") is True
    assert sto.Ontology.is_reserved("STO-A01") is False
    assert onto.is_known("STO-X00") is False


def test_gold_type_lookups() -> None:
    onto = sto.load()
    assert onto.is_objective("STO-A01") is True
    assert onto.gold_type("STO-A01") is GoldType.OBJECTIVE
    assert onto.is_objective("STO-A06") is False
    assert onto.gold_type("STO-P01") is GoldType.ADJUDICATED


def test_classes_in_group() -> None:
    onto = sto.load()
    assert {c.id for c in onto.classes_in_group(ArtifactGroup.A)} == {
        f"STO-A0{i}" for i in range(1, 9)
    }
    assert {c.id for c in onto.classes_in_group(ArtifactGroup.R)} == {"STO-R01", "STO-R02"}


def test_available_versions_includes_default() -> None:
    assert "1.0.0" in sto.available_versions()


def test_unknown_version_raises() -> None:
    with pytest.raises(OntologyError):
        sto.load("9.9.9")


def test_version_is_compatible_with_required() -> None:
    onto = sto.load()
    assert onto.version.satisfies(Version.parse("1.0.0"))
    assert not onto.version.satisfies(Version.parse("2.0.0"))


def test_declared_version_mismatch_is_rejected() -> None:
    onto = sto.load()
    with pytest.raises(OntologyError, match="version mismatch"):
        sto._require_declared_version(onto, "9.9.9")
