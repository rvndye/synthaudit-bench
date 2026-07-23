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

## Anticipated extension points (build via plugins, not core edits)

New detectors, ontology class packs, benchmark tasks, corpora, and figures are
added through the plugin entry-point groups defined in the software
architecture. When one of these is implemented, it moves out of this page.
