"""Unit tests for artifact and gold tuples."""

from __future__ import annotations

import dataclasses

import pytest

from synthaudit_bench.model.enums import Severity
from synthaudit_bench.model.ontology import Disposition, GoldType
from synthaudit_bench.model.tuples import ROWS, ArtifactTuple, GoldTuple


def test_artifact_round_trip_column_set() -> None:
    t = ArtifactTuple(
        support=frozenset({"b", "a"}),
        sto_class="STO-A01",
        disposition=Disposition.STRUCTURAL_CONSTRAINT,
        severity=Severity.MEDIUM,
        evidence={"equation": "a = b"},
        confidence=0.9,
    )
    assert ArtifactTuple.from_mapping(t.to_mapping()) == t
    assert t.to_mapping()["support"] == ["a", "b"]  # sorted


def test_artifact_round_trip_token_support() -> None:
    t = ArtifactTuple(support=ROWS, sto_class="STO-S01", severity=Severity.HIGH)
    assert t.to_mapping()["support"] == "<ROWS>"
    assert ArtifactTuple.from_mapping(t.to_mapping()) == t


def test_artifact_validation() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        ArtifactTuple(support=frozenset(), sto_class="STO-A01")
    with pytest.raises(ValueError, match="token support"):
        ArtifactTuple(support="<NOPE>", sto_class="STO-A01")
    with pytest.raises(ValueError, match="confidence"):
        ArtifactTuple(support=ROWS, sto_class="STO-S01", confidence=1.5)


def test_artifact_is_immutable() -> None:
    t = ArtifactTuple(support=ROWS, sto_class="STO-S01")
    with pytest.raises(dataclasses.FrozenInstanceError):
        t.sto_class = "STO-S02"  # type: ignore[misc]


def test_artifact_hash_is_content_addressed() -> None:
    a = ArtifactTuple(support=frozenset({"a", "b"}), sto_class="STO-A01")
    b = ArtifactTuple(support=frozenset({"b", "a"}), sto_class="STO-A01")
    assert a.content_hash() == b.content_hash()
    assert len(a.content_hash()) == 64
    c = ArtifactTuple(support=frozenset({"a", "b"}), sto_class="STO-A02")
    assert a.content_hash() != c.content_hash()


def test_artifact_sorting_is_deterministic() -> None:
    unordered = [
        ArtifactTuple(support=frozenset({"z"}), sto_class="STO-A02"),
        ArtifactTuple(support=frozenset({"a"}), sto_class="STO-A01"),
        ArtifactTuple(support=frozenset({"b"}), sto_class="STO-A01"),
    ]
    ids = [t.sto_class + "/" + next(iter(t.support)) for t in sorted(unordered)]
    assert ids == ["STO-A01/a", "STO-A01/b", "STO-A02/z"]


def test_gold_round_trip_and_optional() -> None:
    g = GoldTuple(
        support=frozenset({"stab", "stabf"}),
        classes=frozenset({"STO-A07"}),
        dispositions=frozenset({Disposition.TARGET_LEAKAGE}),
        gold_type=GoldType.OBJECTIVE,
        optional=True,
        evidence="stabf == sign(stab)",
    )
    restored = GoldTuple.from_mapping(g.to_mapping())
    assert restored == g
    assert g.to_mapping()["optional"] is True


def test_gold_validation() -> None:
    with pytest.raises(ValueError, match="acceptable class"):
        GoldTuple(
            support=ROWS,
            classes=frozenset(),
            dispositions=frozenset({Disposition.NOT_APPLICABLE}),
            gold_type=GoldType.OBJECTIVE,
        )
    with pytest.raises(ValueError, match="acceptable disposition"):
        GoldTuple(
            support=ROWS,
            classes=frozenset({"STO-S01"}),
            dispositions=frozenset(),
            gold_type=GoldType.OBJECTIVE,
        )


def test_to_canonical_returns_stable_bytes() -> None:
    t = ArtifactTuple(support=ROWS, sto_class="STO-S01")
    assert isinstance(t.to_canonical(), bytes)
    assert t.to_canonical() == t.to_canonical()


def test_gold_canonical_and_hash_without_evidence() -> None:
    g = GoldTuple(
        support=ROWS,
        classes=frozenset({"STO-S01"}),
        dispositions=frozenset({Disposition.NOT_APPLICABLE}),
        gold_type=GoldType.OBJECTIVE,
    )
    assert "evidence" not in g.to_mapping()
    assert isinstance(g.to_canonical(), bytes)
    assert len(g.content_hash()) == 64


def test_from_mapping_rejects_bad_support_type() -> None:
    with pytest.raises(TypeError):
        ArtifactTuple.from_mapping({"support": 123, "class": "STO-A01"})


def test_gold_sorting() -> None:
    a = GoldTuple(
        support=frozenset({"a"}),
        classes=frozenset({"STO-A01"}),
        dispositions=frozenset({Disposition.STRUCTURAL_CONSTRAINT}),
        gold_type=GoldType.OBJECTIVE,
    )
    b = GoldTuple(
        support=frozenset({"b"}),
        classes=frozenset({"STO-A01"}),
        dispositions=frozenset({Disposition.STRUCTURAL_CONSTRAINT}),
        gold_type=GoldType.OBJECTIVE,
    )
    assert sorted([b, a]) == [a, b]
