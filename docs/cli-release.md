# CLI, compliance, and release

WP12 ties the pipeline together: the `bench` command-line interface runs the whole
benchmark, the compliance suite certifies a detector against the specification, and
the release layer produces the manifest and version report. A built-in structural
baseline detector makes the benchmark runnable end-to-end without any external
tool.

## The `bench` CLI

`bench` is the console entry point (`synthaudit_bench.cli.main`). Each subcommand
parses arguments and calls one library function, returning the architecture's exit
codes (0 success; 2 input or validation; 3 integrity; 5 partial dataset failures; 6
policy or compliance block). The commands cover the pipeline end to end:

- `bench version` reports the software, benchmark, ontology, and schema versions.
- `bench registry <root>` lists the datasets in a registry; `bench validate --registry <root>` validates it.
- `bench audit <csv...> --target <col> --out <dir>` audits CSV datasets with the built-in baseline and writes `audits/<id>.json` and `manifest.json`.
- `bench match --audits <dir> --gold <dir>` scores the audits against gold into a metrics table.
- `bench report --audits <dir> --format {json,md}` aggregates the audits into a report.
- `bench compliance <csv...> --gold <dir>` runs the compliance suite and exits 6 if it fails.
- `bench release <csv...>` builds the release manifest and version report.

## The compliance suite

`run_compliance` runs the seven checks of specification Section 11 against a
detector on a conformance set and returns a hash-stamped `ComplianceRecord`: schema
validation of every emitted and consumed artifact (CS-1); byte-identical repeat
runs (CS-2); exact objective-gold recall and precision (CS-3); adjudicated-gold
tolerances of 0.80 (CS-4); abstention correctness, guaranteed by the matching
(CS-5); reproducibility, checked in process as repeat determinism with a
fresh-environment rebuild left to CI (CS-6); and a cross-check of published
reference outputs when supplied (CS-7). Acceptance tolerances are the version-pinned
v1.0 defaults. The record's `result_hash` is cited in a conformance claim.

## The structural baseline detector

`StructuralBaselineDetector` (architecture `detector.adapters.baselines`) is a
reference-free, pandas-only detector for the objective classes that are exactly
determinable from the released table: constant columns (STO-S02), duplicate columns
(STO-A08), and duplicate rows (STO-S01). It is deterministic, operates on the full
data, reads only the immutable dataset, and never imports the reference
implementation. It is registered through the `synthaudit_bench.detectors`
entry-point group, so `discover_detectors` finds it; it exists to prove the task is
non-trivial and to make the benchmark runnable, not as the reference detector.

## Release and versioning

The release layer builds the `MANIFEST.json` that lists every dataset instance (id,
canonical SHA-256, byte size, row and column counts, corpus, split, license, and
source; specification Section 6.1.5) via `dataset_manifest_entry` and
`build_release_manifest`, reports the software, benchmark, ontology, and schema
versions with `version_report`, and enforces the benchmark semver policy with
`check_version_bump` (a MAJOR change requires a major bump, additive a minor bump, a
fix a patch bump; Section 12.2).

## Public API

CLI: `synthaudit_bench.cli.main.main`. Compliance: `run_compliance`,
`ComplianceRecord`, `ComplianceResult`, `DEFAULT_TOLERANCES`. Release:
`version_report`, `build_release_manifest`, `dataset_manifest_entry`,
`ManifestEntry`, `check_version_bump`. Baseline: `StructuralBaselineDetector`,
`builtin_registry`.
