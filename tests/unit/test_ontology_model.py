"""Unit tests for the ontology domain objects."""

from __future__ import annotations

import dataclasses

import pytest

from synthaudit_bench.model import (
    ArtifactGroup,
    ClassDef,
    ColumnRole,
    Deprecation,
    Disposition,
    GoldType,
)


def _class(gold: GoldType = GoldType.OBJECTIVE, dep: Deprecation | None = None) -> ClassDef:
    return ClassDef(
        id="STO-A01",
        name="Linear identity",
        group=ArtifactGroup.A,
        gold_type=gold,
        definition="d",
        scope="s",
        inclusion_criteria="i",
        exclusion_criteria="e",
        example="x",
        counterexample="y",
        relationships=("generalizes STO-A02",),
        operating_points=("tau_exact",),
        deprecation=dep,
    )


def test_gold_type_flags() -> None:
    assert _class(GoldType.OBJECTIVE).is_objective is True
    assert _class(GoldType.ADJUDICATED).is_objective is False


def test_deprecation_flag() -> None:
    assert _class().is_deprecated is False
    dep = Deprecation(since_version="2.0.0", replaced_by="STO-A09", reason="merged")
    assert _class(dep=dep).is_deprecated is True


def test_class_def_is_immutable() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        _class().name = "changed"  # type: ignore[misc]


def test_enum_string_values_match_specification() -> None:
    assert {g.value for g in ArtifactGroup} == {"A", "S", "R", "P"}
    assert {d.value for d in Disposition} == {
        "target_leakage",
        "structural_constraint",
        "redundancy",
        "not_applicable",
    }
    assert ColumnRole.TARGET.value == "target"
    assert len(list(ColumnRole)) == 11
    assert {t.value for t in GoldType} == {"objective", "adjudicated"}
