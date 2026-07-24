"""Unit tests for report-card generation: pillars, BTI, grade, and validation."""

from __future__ import annotations

from typing import Any

import pytest

from synthaudit_bench.model.enums import Grade, Task
from synthaudit_bench.model.ontology import ColumnRole, Disposition
from synthaudit_bench.model.records import Transparency
from synthaudit_bench.model.report import Pillars, Provenance
from synthaudit_bench.model.results import DetectorInfo
from synthaudit_bench.model.tuples import ArtifactTuple
from synthaudit_bench.report import (
    PillarInputs,
    bti,
    build_report_card,
    dispositions_summary,
    feature_pillar,
    grade_for,
    transparency_pillar,
)
from synthaudit_bench.report.errors import ReportError

_PROV = Provenance("2026-07-24T00:00:00Z", 42, "cfg")
_DETECTOR = DetectorInfo("synthaudit", "0.1.0")


def test_transparency_pillar() -> None:
    assert transparency_pillar(None) is None
    assert transparency_pillar(Transparency(True, False, False, False)) == 0.25
    assert transparency_pillar(Transparency(True, True, True, True)) == 1.0


def test_feature_pillar() -> None:
    assert feature_pillar(None, 4) is None
    roles = {"a": ColumnRole.CONSTANT, "b": ColumnRole.INPUT, "t": ColumnRole.TARGET}
    assert feature_pillar(roles, 3) == pytest.approx(0.5)  # 1 bad of max(3-1,1)=2
    assert feature_pillar({"a": ColumnRole.DUPLICATE}, 1) == pytest.approx(0.0)  # max(p-1,1)=1


def test_bti_over_available_pillars() -> None:
    assert bti(Pillars()) is None
    value = bti(Pillars(feature=1.0, transparency=1.0))
    assert value == pytest.approx(1.0)
    low = bti(Pillars(label=0.0))  # floored at epsilon 0.01
    assert low == pytest.approx(0.01)


@pytest.mark.parametrize(
    "value,grade",
    [
        (None, None),
        (0.85, Grade.A),
        (0.7, Grade.B),
        (0.55, Grade.C),
        (0.4, Grade.D),
        (0.1, Grade.F),
    ],
)
def test_grade_for(value: float | None, grade: Grade | None) -> None:
    assert grade_for(value) is grade


def test_dispositions_summary() -> None:
    arts = [
        ArtifactTuple(frozenset({"a"}), "STO-A01", disposition=Disposition.TARGET_LEAKAGE),
        ArtifactTuple(frozenset({"b"}), "STO-A01", disposition=Disposition.TARGET_LEAKAGE),
        ArtifactTuple(frozenset({"c"}), "STO-S02"),  # no disposition
    ]
    assert dispositions_summary(arts) == {"target_leakage": 2}


def test_build_report_card_full() -> None:
    card = build_report_card(
        dataset_id="grid",
        dataset_sha256="a" * 64,
        sto_version="1.0.0",
        implementation=_DETECTOR,
        target="stabf",
        task=Task.CLASSIFICATION,
        provenance=_PROV,
        artifacts=[
            ArtifactTuple(
                frozenset({"stab", "stabf"}), "STO-A07", disposition=Disposition.TARGET_LEAKAGE
            )
        ],
        transparency=Transparency(True, False, False, False),
        column_roles={"stabf": ColumnRole.TARGET, "stab": ColumnRole.LEAKY_FEATURE},
        n_cols=2,
        pillar_inputs=PillarInputs(label=0.0, realism=0.72, information=1.0),
        probe_family="trees",
    )
    assert card.grade is not None
    assert card.bti is not None
    assert card.pillars is not None and card.pillars.transparency == 0.25
    assert card.probe_family == "trees"


def test_build_report_card_no_pillars() -> None:
    card = build_report_card(
        dataset_id="d",
        dataset_sha256="a" * 64,
        sto_version="1.0.0",
        implementation=_DETECTOR,
        target=None,
        task=Task.NONE,
        provenance=_PROV,
    )
    assert card.pillars is None
    assert card.bti is None
    assert card.grade is None
    assert card.dispositions_summary is None


def test_build_report_card_schema_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    from synthaudit_bench.schemas.errors import SchemaValidationError

    def _boom(name: str, instance: Any, version: str | None = None) -> None:
        raise SchemaValidationError(
            schema_id="report-card", pointer="/", value="x", explanation="no"
        )

    monkeypatch.setattr("synthaudit_bench.report.reportcard.schemas.validate_instance", _boom)
    with pytest.raises(ReportError, match="failed schema validation"):
        build_report_card(
            dataset_id="d",
            dataset_sha256="a" * 64,
            sto_version="1.0.0",
            implementation=_DETECTOR,
            target=None,
            task=Task.NONE,
            provenance=_PROV,
        )


def test_build_report_card_validate_false() -> None:
    card = build_report_card(
        dataset_id="d",
        dataset_sha256="a" * 64,
        sto_version="1.0.0",
        implementation=_DETECTOR,
        target=None,
        task=Task.NONE,
        provenance=_PROV,
        validate=False,
    )
    assert card.dataset_id == "d"
