# Aggregation, report cards, and statistics

The `synthaudit_bench.report` package is the pure reporting layer: it turns a run's
audit results and scored metrics into report cards, tidy tables and summaries,
frame-proportion statistics, declarative figure specifications, and JSON and
Markdown reports. Everything is deterministic and reads only its inputs.

## Report cards

`build_report_card` produces the standardized report card (specification Section
8). The Benchmark Trustworthiness Index and its grade bands are computed exactly as
in Appendix D.3: the index is the weighted geometric mean of the available pillars
(weights L 0.30, F 0.20, H 0.20, R 0.15, I 0.15, T 0.15, floor 0.01, normalized by
the summed weight of the present pillars), and the grade bands are A ≥ 0.80, B ≥
0.65, C ≥ 0.50, D ≥ 0.35, else F. A pillar that is not available is null and
excluded from the index, so a card computed from only the metadata-derived pillars
is still valid.

Two pillars are computed here because they are fully determined by inputs this
layer holds: T (transparency) is the fraction of the four disclosure booleans that
are true, and F (feature integrity) is one minus the share of non-target columns
carrying an artifact-bearing role. The learned and statistical pillars (L, H, R, I)
depend on probe families and fit statistics that the specification leaves to the
implementation (Section 10.3), so they are supplied as `PillarInputs` and are null
when not provided. This layer never runs a learner and never fabricates a
statistic.

## Aggregation

The aggregation functions produce deterministic long-format tidy rows (`finding_rows`,
one row per artifact; `dataset_rows`, one row per dataset; `per_dataset_metric_rows`,
one row per dataset of detection, disposition, and partial F1 from a scored metrics
table) and summaries (`per_dataset_summary`, `per_detector_summary`, `sto_summary`,
`benchmark_summary`). Every row set is sorted, so the same results always aggregate
to the same tables.

## Statistics

`frame_proportions` reports the exact proportion of an enumerated frame carrying
each value. The Census Corpus is a frame, not a random sample, so these are frame
proportions, not population estimates, and sampling confidence intervals are
deliberately not emitted (Blueprint RT-F1, specification Section 3.3 L3). A
measurement-error bound reflects detector error rather than sampling and therefore
depends on a separately characterized detector error rate supplied by the caller;
it is not fabricated.

## Figures and reports

`standard_figures` returns declarative `FigureSpec` values that name a tidy table
and an encoding and carry no rendering logic, so a figure is reproducible from the
specification and the table. `build_report` assembles the summaries, tidy tables,
frame proportions, and the optional metrics table and manifest into one report
mapping, and it carries the figure set alongside every tidy table those figures
consume: `sto_summary` (class prevalence), `findings` (disposition breakdown), and
`per_dataset_metrics` (detection F1 by dataset). Every `FigureSpec` input therefore
resolves against a table present in the same report mapping, so a figure is never a
dangling reference to a table the report does not emit; `per_dataset_metrics` is
present but empty when no metrics table is supplied. `render_json_report` renders the
mapping as deterministic JSON and `render_markdown_report` as a human-readable
Markdown document.

## Public API

Report cards: `build_report_card`, `bti`, `grade_for`, `PillarInputs`,
`transparency_pillar`, `feature_pillar`, `dispositions_summary`. Aggregation:
`finding_rows`, `dataset_rows`, `per_dataset_metric_rows`, `per_dataset_summary`,
`per_detector_summary`, `sto_summary`, `benchmark_summary`. Statistics: `frame_proportions`,
`FrameProportion`. Figures: `standard_figures` and the individual builders. Reports:
`build_report`, `render_json_report`, `render_markdown_report`.
