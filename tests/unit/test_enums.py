"""Unit tests for the domain-model enumerations."""

from __future__ import annotations

from synthaudit_bench.model.enums import (
    FrameStratum,
    GeneratorFamily,
    Grade,
    ProvenanceConfidence,
    Severity,
    Task,
)


def test_enum_values_match_specification() -> None:
    assert {s.value for s in Severity} == {"critical", "high", "medium", "low"}
    assert {g.value for g in Grade} == {"A", "B", "C", "D", "F"}
    assert {f.value for f in FrameStratum} == {
        "census",
        "planted",
        "controlled",
        "adjudicated_real",
    }
    assert {p.value for p in ProvenanceConfidence} == {"documented", "inferred", "unknown"}
    assert {t.value for t in Task} == {"classification", "regression", "none"}
    assert GeneratorFamily.PHYSICS_SIMULATOR.value == "physics-simulator"
    assert len(list(GeneratorFamily)) == 10
