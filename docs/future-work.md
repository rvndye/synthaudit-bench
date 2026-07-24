# Future work (out of scope for this benchmark version)

This page is the sink for ideas that are deliberately **not** implemented now.
Per the scope discipline in the Final Blueprint and Execution Manual, work that
belongs to a future paper, a future tool version, a future benchmark or ontology
revision, a future detector, or future governance is recorded here rather than
built. Adding an item here is the correct response to a good but out-of-scope
idea.

## Deferred by decision (see the Final Blueprint)

- **Live leaderboard and challenge track.** Substrate (tool-agnostic task, gold,
  baselines) is in scope; launching a running competition is deferred until a
  second independent auditing method exists.
- **Certification program.** A descriptive report card is in scope; a pass/fail
  certification seal is deferred (premature authority).
- **Continuous auditing / audit-on-submit service.** Deferred; the report-card
  schema is designed to allow it later.
- **Annual release cadence.** A versioning scheme is in scope; a cadence promise
  is deferred until a maintainer plan exists.
- **Generator trustworthiness ranking.** Out of scope; the controlled study
  reports family signatures descriptively, never a ranking.

## Deferred to later papers / tool versions

- **Temporal, relational, and latent-artifact detectors** (tool v0.2+ and later
  papers). New ontology classes and corpus strata, not a redo of this study.
- **Membership-inference and formal privacy auditing.** A different axis; out of
  scope for structural trustworthiness.
- **Method-comparison paper** (needs a second tool) and the **longitudinal trend
  paper** (needs multiple benchmark versions over time).

## Deferred release-candidate audit findings (address in a future major release)

The pre-release software audit accepted the implementation and its verified Major
findings (runner capability-discovery isolation, figure-table integration, and CLI
reconciliation) plus four localized Minor findings (F-pillar clamp, duplicate-id
guard, immutable thresholds, empty-audits exit code) were remediated in the release
candidate. The remaining findings are deliberately **not** implemented now, because
each is either a refactor, a report-semantics change forbidden by the frozen
specification, or a new feature; they are recorded here for a future major release.

- **MIN-1 — Deduplicate `_detector_info`.** The helper exists in both
  `detector/run.py` (from capabilities) and `runner/engine.py` (from a detector) and
  builds `DetectorInfo` identically. A shared helper in `detector.base` would remove
  the duplication, but that edits the frozen detector-protocol module for a cosmetic
  win; deferred to avoid touching a public-API boundary in an RC.
- **MIN-2 — Unify the CSV read paths.** The CLI's `_load_csv` is a second
  faithful-read path that skips WP7 `verify_dataset`/integrity. It is now documented
  as an intentional convenience (see `docs/cli-release.md`); folding it onto a single
  shared helper is the future code change.
- **MIN-5 — Class-prevalence denominator.** `frame_proportions` used for class
  prevalence counts findings, not distinct datasets, so many findings of one class in
  one dataset inflate that class's prevalence. Correcting it changes report
  semantics, which the RC scope freezes; it is deferred to a version that may revise
  the reporting contract, with the current behavior documented as a characterization
  caveat.
- **MIN-7 — Relocate `MissingFileError`.** The `load`/`acquire` coupling is resolved
  by a lazy import inside `verify_source_checksums`. It is correct and passes the
  import-linter contract, but a shared errors module would be cleaner. Deferred as a
  refactor.
- **MIN-9 — Human-readable report cards.** Report cards are JSON-only; there is no
  Appendix C.3-style card-to-Markdown renderer. Adding one is a new feature, deferred.
- **Cosmetic (COS-1..COS-5).** Builtin-name shadowing of `id`/`license` in the
  manifest entry (COS-1); group extraction by string slicing in
  `DetectorCapabilities.supports_class` (COS-2); an un-commented recursion ceiling in
  the Kuhn matcher and `_json_primitive` (COS-3); the wide keyword-only signature of
  `build_report_card` (COS-4); and the untracked delivered `.bundle`/`.zip` in the
  repo root that a careless `git add .` could commit (COS-5). All are cosmetic and
  deferred; none affects behavior, determinism, or the public contract.

## Anticipated extension points (build via plugins, not core edits)

New detectors, ontology class packs, benchmark tasks, corpora, and figures are
added through the plugin entry-point groups defined in the software
architecture. When one of these is implemented, it moves out of this page.
