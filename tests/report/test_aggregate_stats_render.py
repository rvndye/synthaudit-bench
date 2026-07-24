"""Unit tests for aggregation, statistics, figures, and report rendering."""

from __future__ import annotations

import json

import pytest

from synthaudit_bench.model.manifest import Environment, RunManifest, Timestamps
from synthaudit_bench.model.metrics import AggregateScores, CoverageReport, MetricsTable, Score
from synthaudit_bench.model.ontology import Disposition
from synthaudit_bench.model.results import AuditResult, DetectorInfo, ErrorRecord
from synthaudit_bench.model.tuples import ROWS, ArtifactTuple
from synthaudit_bench.report import (
    benchmark_summary,
    build_report,
    dataset_rows,
    finding_rows,
    frame_proportions,
    per_dataset_summary,
    per_detector_summary,
    render_json_report,
    render_markdown_report,
    standard_figures,
    sto_summary,
)
from synthaudit_bench.report.stats import FrameProportion

_DET = DetectorInfo("t", "1")
_RESULTS = [
    AuditResult(
        "d1",
        "h1",
        _DET,
        (
            ArtifactTuple(
                frozenset({"a", "b"}), "STO-A01", disposition=Disposition.STRUCTURAL_CONSTRAINT
            ),
            ArtifactTuple(ROWS, "STO-R02"),
        ),
    ),
    AuditResult("d2", "h2", _DET, (ArtifactTuple(frozenset({"x"}), "STO-S02"),)),
    AuditResult("d3", "h3", _DET, error=ErrorRecord("resource", "timeout")),
]


def test_finding_rows_handles_token_and_set_support() -> None:
    rows = finding_rows(_RESULTS)
    assert len(rows) == 3
    supports = {
        tuple(r["support"]) if isinstance(r["support"], list) else r["support"] for r in rows
    }
    assert ROWS in supports
    assert ("a", "b") in supports


def test_dataset_rows_and_summaries() -> None:
    rows = dataset_rows(_RESULTS)
    assert [r["status"] for r in rows] == ["scored", "scored", "resource"]
    assert rows[2]["error"] == "resource"
    assert per_dataset_summary(_RESULTS)[0] == {
        "dataset_id": "d1",
        "status": "scored",
        "n_findings": 2,
    }


def test_per_detector_summary() -> None:
    summary = per_detector_summary(_DET, _RESULTS)
    assert summary == {
        "detector": "t",
        "version": "1",
        "n_datasets": 3,
        "n_scored": 2,
        "n_failed": 1,
        "n_findings": 3,
    }


def test_sto_summary_sorted() -> None:
    summary = sto_summary(_RESULTS)
    assert [row["sto_class"] for row in summary] == ["STO-A01", "STO-R02", "STO-S02"]
    assert all(row["count"] == 1 for row in summary)


def test_benchmark_summary() -> None:
    summary = benchmark_summary(_RESULTS, split="public-dev")
    assert summary["n_datasets"] == 3
    assert summary["n_scored"] == 2
    assert summary["n_classes"] == 3


def test_frame_proportions_exact_no_ci() -> None:
    proportions = frame_proportions(finding_rows(_RESULTS), "sto_class")
    assert [p.value for p in proportions] == ["STO-A01", "STO-R02", "STO-S02"]
    assert all(p.total == 3 for p in proportions)
    assert proportions[0].proportion == pytest.approx(1 / 3)


def test_frame_proportion_empty_and_bounds() -> None:
    assert frame_proportions([], "sto_class") == ()
    empty = FrameProportion("x", 0, 0)
    assert empty.proportion == 0.0
    fp = FrameProportion("x", 9, 10)  # 0.9
    high_low, high_high = fp.measurement_error_bound(0.5)  # high clamped
    assert high_low == pytest.approx(0.4)
    assert high_high == 1.0
    low = FrameProportion("y", 1, 10)  # 0.1
    low_low, low_high = low.measurement_error_bound(0.5)  # low clamped
    assert low_low == 0.0
    assert low_high == pytest.approx(0.6)
    assert fp.to_mapping()["count"] == 9


def test_standard_figures() -> None:
    figures = standard_figures()
    assert [f.id for f in figures] == ["class-prevalence", "detector-f1", "disposition-breakdown"]
    assert figures[0].inputs[0].table == "sto_summary"


def _metrics() -> MetricsTable:
    micro = AggregateScores(Score(0.8, 1.0, 0.888, 4, 1, 0), 0.5, 0.5)
    return MetricsTable(
        split="public-dev", detection=micro, disposition_aware=micro, coverage=CoverageReport()
    )


def _manifest() -> RunManifest:
    return RunManifest(
        bench_version="1.0.0",
        sto_version="1.0.0",
        schema_version="1.0.0",
        split="public-dev",
        detector=_DET,
        config_hash="",
        environment=Environment("3.11", "linux"),
        root_seed=42,
        limits=__import__(
            "synthaudit_bench.model.config", fromlist=["ResourceLimits"]
        ).ResourceLimits(),
        timestamps=Timestamps("t0", "t1"),
    )


def test_build_report_minimal() -> None:
    report = build_report(_RESULTS, split="public-dev")
    assert report["summary"]["n_datasets"] == 3
    assert "detector_summary" not in report
    assert "metrics" not in report


def test_build_report_full_and_render() -> None:
    report = build_report(
        _RESULTS, split="public-dev", detector=_DET, metrics=_metrics(), manifest=_manifest()
    )
    assert "detector_summary" in report and "metrics" in report and "manifest" in report
    js = render_json_report(report)
    assert json.loads(js)["split"] == "public-dev"
    assert (
        render_json_report(
            build_report(
                _RESULTS,
                split="public-dev",
                detector=_DET,
                metrics=_metrics(),
                manifest=_manifest(),
            )
        )
        == js
    )
    md = render_markdown_report(report)
    assert md.startswith("# SynthAudit-Bench report: public-dev")
    assert "Detection micro-F1" in md
    assert "STO-A01" in md


def test_render_markdown_without_detector_or_metrics() -> None:
    md = render_markdown_report(build_report(_RESULTS, split="s"))
    assert "## Metrics" not in md
    assert "## STO class prevalence" in md
