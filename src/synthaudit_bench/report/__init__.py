"""Aggregation, report cards, statistics, figures, and reports (architecture L2).

The pure reporting layer: it turns a run's audit results and scored metrics into
report cards (the Section 8 card with the Appendix D.3 Benchmark Trustworthiness
Index and grade), deterministic tidy tables and summaries, frame-proportion
statistics (no sampling confidence intervals, Blueprint RT-F1), declarative figure
specifications, and JSON and Markdown reports. Everything is deterministic and
reads only its inputs.

Public API: report cards (`build_report_card`, `bti`, `grade_for`, `PillarInputs`);
aggregation (`finding_rows`, `dataset_rows`, `per_dataset_summary`,
`per_detector_summary`, `sto_summary`, `benchmark_summary`); statistics
(`frame_proportions`, `FrameProportion`); figures (`standard_figures`); and reports
(`build_report`, `render_json_report`, `render_markdown_report`).
"""

from __future__ import annotations

from synthaudit_bench.report.aggregate import (
    benchmark_summary,
    dataset_rows,
    finding_rows,
    per_dataset_summary,
    per_detector_summary,
    sto_summary,
)
from synthaudit_bench.report.errors import ReportError
from synthaudit_bench.report.figures import (
    class_prevalence_figure,
    detector_f1_figure,
    disposition_breakdown_figure,
    standard_figures,
)
from synthaudit_bench.report.render import (
    build_report,
    render_json_report,
    render_markdown_report,
)
from synthaudit_bench.report.reportcard import (
    PillarInputs,
    bti,
    build_report_card,
    dispositions_summary,
    feature_pillar,
    grade_for,
    transparency_pillar,
)
from synthaudit_bench.report.stats import FrameProportion, frame_proportions

__all__ = [
    "FrameProportion",
    "PillarInputs",
    "ReportError",
    "benchmark_summary",
    "bti",
    "build_report",
    "build_report_card",
    "class_prevalence_figure",
    "dataset_rows",
    "detector_f1_figure",
    "disposition_breakdown_figure",
    "dispositions_summary",
    "feature_pillar",
    "finding_rows",
    "frame_proportions",
    "grade_for",
    "per_dataset_summary",
    "per_detector_summary",
    "render_json_report",
    "render_markdown_report",
    "standard_figures",
    "sto_summary",
    "transparency_pillar",
]
