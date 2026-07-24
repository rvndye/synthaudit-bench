"""Assemble and render benchmark reports in JSON and Markdown.

``build_report`` gathers the deterministic summaries, tidy tables, and frame
proportions (and the optional metrics table and run manifest) into one report
mapping; ``render_json_report`` and ``render_markdown_report`` render it. Both
renderers are pure and deterministic: the same report mapping always renders to the
same bytes.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from synthaudit_bench.model.manifest import RunManifest
from synthaudit_bench.model.metrics import MetricsTable
from synthaudit_bench.model.results import AuditResult, DetectorInfo
from synthaudit_bench.report.aggregate import (
    benchmark_summary,
    finding_rows,
    per_dataset_metric_rows,
    per_dataset_summary,
    per_detector_summary,
    sto_summary,
)
from synthaudit_bench.report.figures import standard_figures
from synthaudit_bench.report.stats import frame_proportions

__all__ = ["build_report", "render_json_report", "render_markdown_report"]


def build_report(
    results: Sequence[AuditResult],
    *,
    split: str,
    detector: DetectorInfo | None = None,
    metrics: MetricsTable | None = None,
    manifest: RunManifest | None = None,
) -> dict[str, Any]:
    """Assemble the deterministic benchmark report mapping for a split.

    The report carries the standard figure specifications alongside every tidy table
    they consume, so each :class:`~synthaudit_bench.model.figures.FigureSpec` input
    resolves against a table present in the report: ``sto_summary`` (class prevalence),
    ``findings`` (disposition breakdown), and ``per_dataset_metrics`` (detection F1 by
    dataset). ``per_dataset_metrics`` is empty when no metrics table is supplied.
    """
    findings = finding_rows(results)
    report: dict[str, Any] = {
        "split": split,
        "summary": benchmark_summary(results, split=split),
        "per_dataset": list(per_dataset_summary(results)),
        "sto_summary": list(sto_summary(results)),
        "findings": list(findings),
        "per_dataset_metrics": (
            list(per_dataset_metric_rows(metrics)) if metrics is not None else []
        ),
        "figures": [figure.to_mapping() for figure in standard_figures()],
        "class_proportions": [p.to_mapping() for p in frame_proportions(findings, "sto_class")],
    }
    if detector is not None:
        report["detector_summary"] = per_detector_summary(detector, results)
    if metrics is not None:
        report["metrics"] = metrics.to_mapping()
    if manifest is not None:
        report["manifest"] = manifest.to_mapping()
    return report


def render_json_report(report: dict[str, Any]) -> str:
    """Render a report mapping as deterministic, pretty-printed JSON."""
    return json.dumps(report, sort_keys=True, indent=2)


def _table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return lines


def render_markdown_report(report: dict[str, Any]) -> str:
    """Render a report mapping as a human-readable Markdown document."""
    summary = report["summary"]
    lines: list[str] = [
        f"# SynthAudit-Bench report: {report['split']}",
        "",
        f"Datasets: {summary['n_datasets']} "
        f"({summary['n_scored']} scored, {summary['n_failed']} failed). "
        f"Findings: {summary['n_findings']} across {summary['n_classes']} classes.",
        "",
    ]
    if "detector_summary" in report:
        det = report["detector_summary"]
        lines += [f"Detector: {det['detector']} {det['version']}.", ""]
    if "metrics" in report:
        micro = report["metrics"]["detection"]["micro"]
        disp = report["metrics"]["disposition_aware"]["micro"]
        detection_line = (
            f"Detection micro-F1: {micro['f1']:.4f} "
            f"(P {micro['precision']:.4f}, R {micro['recall']:.4f})."
        )
        lines += [
            "## Metrics",
            "",
            detection_line,
            f"Disposition-aware micro-F1: {disp['f1']:.4f}.",
            "",
        ]
    lines += ["## STO class prevalence", ""]
    lines += _table(
        ["Class", "Count", "Datasets"],
        [(row["sto_class"], row["count"], row["n_datasets"]) for row in report["sto_summary"]],
    )
    lines += ["", "## Per-dataset", ""]
    lines += _table(
        ["Dataset", "Status", "Findings"],
        [(row["dataset_id"], row["status"], row["n_findings"]) for row in report["per_dataset"]],
    )
    return "\n".join(lines) + "\n"
