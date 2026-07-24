"""Release-candidate regression tests for the report layer (MIN-3, MAJ-2).

MIN-3: the F (feature integrity) pillar is clamped to the [0, 1] pillar domain even
when the artifact-bearing column count exceeds ``p - 1``. MAJ-2: the report carries
the standard figure specifications and every tidy table those figures consume, so no
figure input names a table that is absent from the report (no dangling reference).
"""

from __future__ import annotations

from synthaudit_bench.model.metrics import (
    AggregateScores,
    CoverageReport,
    DatasetMetrics,
    MetricsTable,
    Score,
)
from synthaudit_bench.model.ontology import ColumnRole
from synthaudit_bench.report.aggregate import per_dataset_metric_rows
from synthaudit_bench.report.render import build_report
from synthaudit_bench.report.reportcard import feature_pillar


def _score(f1: float) -> Score:
    return Score(precision=f1, recall=f1, f1=f1, tp=1, fp=0, fn=0)


def _metrics() -> MetricsTable:
    aggregate = AggregateScores(micro=_score(0.8), macro_class_f1=0.8, macro_dataset_f1=0.8)
    return MetricsTable(
        split="public-dev",
        detection=aggregate,
        disposition_aware=aggregate,
        coverage=CoverageReport(),
        per_dataset=(
            DatasetMetrics("d2", _score(0.5), _score(0.4)),
            DatasetMetrics("d1", _score(0.9), _score(0.8), partial_credit=_score(0.95)),
        ),
    )


def test_feature_pillar_clamped_to_unit_interval() -> None:
    # Two artifact-bearing columns in a two-column frame: raw value 1 - 2/1 = -1.0.
    roles = {"a": ColumnRole.CONSTANT, "b": ColumnRole.DUPLICATE}
    assert feature_pillar(roles, 2) == 0.0


def test_feature_pillar_normal_case_is_unchanged() -> None:
    # One bearing column of three: 1 - 1/max(3 - 1, 1) = 0.5, unaffected by the clamp.
    roles = {"a": ColumnRole.CONSTANT, "b": ColumnRole.INPUT, "c": ColumnRole.INPUT}
    assert feature_pillar(roles, 3) == 0.5


def test_per_dataset_metric_rows_ordered_and_shaped() -> None:
    rows = per_dataset_metric_rows(_metrics())
    # MetricsTable orders per_dataset by id, so the rows are deterministic.
    assert [row["dataset_id"] for row in rows] == ["d1", "d2"]
    assert rows[0] == {
        "dataset_id": "d1",
        "detection_f1": 0.9,
        "disposition_f1": 0.8,
        "partial_f1": 0.95,
    }
    assert rows[1]["partial_f1"] is None


def test_report_carries_figures_and_all_input_tables() -> None:
    report = build_report([], split="public-dev", metrics=_metrics())
    assert {"figures", "findings", "per_dataset_metrics"} <= set(report)
    input_tables = {
        figure_input["table"] for figure in report["figures"] for figure_input in figure["inputs"]
    }
    # Every figure input names a table present in the report: no dangling references.
    assert input_tables == {"sto_summary", "findings", "per_dataset_metrics"}
    assert input_tables <= set(report)
    assert report["per_dataset_metrics"] == list(per_dataset_metric_rows(_metrics()))


def test_report_without_metrics_still_resolves_figure_tables() -> None:
    report = build_report([], split="public-dev")
    input_tables = {
        figure_input["table"] for figure in report["figures"] for figure_input in figure["inputs"]
    }
    # The per_dataset_metrics table is present but empty when no metrics are supplied.
    assert input_tables <= set(report)
    assert report["per_dataset_metrics"] == []
