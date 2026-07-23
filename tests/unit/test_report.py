"""Unit tests for the report card and its value objects."""

from __future__ import annotations

import dataclasses

import pytest

from synthaudit_bench.model.enums import Grade, Task
from synthaudit_bench.model.ontology import ColumnRole, Disposition
from synthaudit_bench.model.report import Pillars, Provenance, Recommendations, ReportCard
from synthaudit_bench.model.results import DetectorInfo
from synthaudit_bench.model.tuples import ArtifactTuple

_DET = DetectorInfo(name="synthaudit", version="0.1.0")
_PROV = Provenance(run_timestamp="2026-07-23T00:00:00Z", seed=42, config_hash="c0ffee")
_ART = ArtifactTuple(
    support=frozenset({"stab", "stabf"}),
    sto_class="STO-A07",
    disposition=Disposition.TARGET_LEAKAGE,
)


def _card(**overrides: object) -> ReportCard:
    base: dict[str, object] = {
        "schema_version": "1.0.0",
        "dataset_id": "grid",
        "dataset_sha256": "h" * 64,
        "sto_version": "1.0.0",
        "implementation": _DET,
        "target": "stabf",
        "task": Task.CLASSIFICATION,
        "provenance": _PROV,
        "artifacts": (_ART,),
    }
    base.update(overrides)
    return ReportCard(**base)  # type: ignore[arg-type]


def test_pillars_round_trip_with_nulls() -> None:
    pillars = Pillars(label=0.0, feature=0.85, transparency=None)
    mapping = pillars.to_mapping()
    assert mapping == {"L": 0.0, "F": 0.85, "H": None, "R": None, "I": None, "T": None}
    assert Pillars.from_mapping(mapping) == pillars


def test_recommendations_round_trip() -> None:
    rec = Recommendations(drop=("a",), protocol_warnings=("use grouped CV",))
    assert Recommendations.from_mapping(rec.to_mapping()) == rec


def test_report_card_minimal_round_trip() -> None:
    card = _card()
    assert ReportCard.from_mapping(card.to_mapping()) == card


def test_report_card_full_round_trip() -> None:
    card = _card(
        column_roles={"stabf": ColumnRole.TARGET, "stab": ColumnRole.LABEL_COMPONENT},
        dispositions_summary={"target_leakage": 1},
        pillars=Pillars(label=0.0, feature=0.85),
        bti=0.23,
        grade=Grade.F,
        probe_family="gbm",
        recommendations=Recommendations(drop=("stab",)),
    )
    assert ReportCard.from_mapping(card.to_mapping()) == card


def test_content_hash_excludes_provenance() -> None:
    a = _card(provenance=Provenance("2026-01-01T00:00:00Z", 42, "c0ffee"))
    b = _card(provenance=Provenance("2027-12-31T23:59:59Z", 42, "c0ffee"))
    assert a.content_hash() == b.content_hash()
    assert isinstance(a.to_canonical(), bytes)
    assert a.to_mapping()["provenance"]["run_timestamp"] == "2026-01-01T00:00:00Z"


def test_content_hash_is_content_addressed() -> None:
    assert _card().content_hash() != _card(grade=Grade.A, bti=0.9).content_hash()
    assert len(_card().content_hash()) == 64


def test_artifacts_normalized_to_sorted_order() -> None:
    a = ArtifactTuple(support=frozenset({"z"}), sto_class="STO-A02")
    b = ArtifactTuple(support=frozenset({"a"}), sto_class="STO-A01")
    card = _card(artifacts=(a, b))
    assert card.artifacts == (b, a)


def test_report_card_is_immutable() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        _card().dataset_id = "x"  # type: ignore[misc]
